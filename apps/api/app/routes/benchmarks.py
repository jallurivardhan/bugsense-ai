from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.db.models import BenchmarkRun

router = APIRouter()


class BenchmarkConfig(BaseModel):
    name: str
    model: str
    temperature: float = 0.7


class BenchmarkCreate(BaseModel):
    name: str = Field(..., min_length=1)
    dataset_version: str
    model_configs: Optional[List[BenchmarkConfig]] = None


class BenchmarkResult(BaseModel):
    base_model: Dict[str, Any]
    fine_tuned: Dict[str, Any]
    dpo_tuned: Dict[str, Any]


class BenchmarkRunResponse(BaseModel):
    id: UUID
    name: str
    dataset_version: str
    model_configs: List[Dict[str, Any]]
    results: BenchmarkResult
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
    }


class BenchmarkRunListResponse(BaseModel):
    items: List[BenchmarkRunResponse]
    total: int


def _to_benchmark_response(model: BenchmarkRun) -> BenchmarkRunResponse:
    results = model.results or {}

    mock_results = {
        "base_model": {
            "accuracy": 0.72,
            "f1": 0.68,
            "schema_valid_rate": 0.85,
            "avg_latency_ms": 1200,
        },
        "fine_tuned": {
            "accuracy": 0.89,
            "f1": 0.87,
            "schema_valid_rate": 0.97,
            "avg_latency_ms": 1150,
        },
        "dpo_tuned": {
            "accuracy": 0.91,
            "f1": 0.90,
            "schema_valid_rate": 0.98,
            "avg_latency_ms": 1180,
        },
    }

    merged_results = {**mock_results, **results}

    return BenchmarkRunResponse(
        id=model.id,
        name=model.name,
        dataset_version=model.dataset_version,
        model_configs=model.model_configs,
        results=BenchmarkResult(**merged_results),
        created_at=model.created_at,
    )


@router.post(
    "",
    response_model=BenchmarkRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_benchmark_run(
    payload: BenchmarkCreate,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkRunResponse:
    model_configs = (
        [config.model_dump() for config in payload.model_configs]
        if payload.model_configs
        else []
    )

    mock_results = {
        "base_model": {
            "accuracy": 0.72,
            "f1": 0.68,
            "schema_valid_rate": 0.85,
            "avg_latency_ms": 1200,
        },
        "fine_tuned": {
            "accuracy": 0.89,
            "f1": 0.87,
            "schema_valid_rate": 0.97,
            "avg_latency_ms": 1150,
        },
        "dpo_tuned": {
            "accuracy": 0.91,
            "f1": 0.90,
            "schema_valid_rate": 0.98,
            "avg_latency_ms": 1180,
        },
    }

    instance = BenchmarkRun(
        name=payload.name,
        dataset_version=payload.dataset_version,
        model_configs=model_configs,
        results=mock_results,
    )

    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    return _to_benchmark_response(instance)


@router.get("", response_model=BenchmarkRunListResponse)
async def list_benchmark_runs(
    db: AsyncSession = Depends(get_db),
) -> BenchmarkRunListResponse:
    stmt_total: Select[tuple[int]] = select(BenchmarkRun).order_by(
        BenchmarkRun.created_at.desc()
    )
    result = await db.execute(stmt_total)
    rows: List[BenchmarkRun] = list(result.scalars().all())

    total = len(rows)

    return BenchmarkRunListResponse(
        items=[_to_benchmark_response(row) for row in rows],
        total=total,
    )


@router.get("/{id}", response_model=BenchmarkRunResponse)
async def get_benchmark_run(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkRunResponse:
    stmt = select(BenchmarkRun).where(BenchmarkRun.id == id)
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark run not found",
        )

    return _to_benchmark_response(instance)

