from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.db.models import BugAnalysis
from app.schemas import (
    BugAnalysisCreate,
    BugAnalysisListResponse,
    BugAnalysisResponse,
    BugAnalysisResult,
)

router = APIRouter()


def _to_bug_analysis_response(model: BugAnalysis) -> BugAnalysisResponse:
    result = BugAnalysisResult(
        severity=model.severity,
        priority=model.priority,
        component=model.component,
        repro_steps=(model.repro_steps.split("\n") if model.repro_steps else None),
        reasoning=model.reasoning,
        missing_info=(model.missing_info.split("\n") if model.missing_info else None),
    )

    return BugAnalysisResponse(
        id=model.id,
        title=model.title,
        description=model.description,
        environment=model.environment,
        result=result,
        model_version=model.model_version,
        prompt_version=model.prompt_version,
        latency_ms=model.latency_ms,
        schema_valid=model.schema_valid,
        created_at=model.created_at,
    )


@router.post(
    "",
    response_model=BugAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bug_analysis(
    payload: BugAnalysisCreate, db: AsyncSession = Depends(get_db)
) -> BugAnalysisResponse:
    mock_result = {
        "severity": "High",
        "priority": "P1",
        "component": "Authentication",
        "repro_steps": [
            "Open login page",
            "Enter invalid credentials",
            "Click submit",
        ],
        "reasoning": (
            "Based on the description, this appears to be a critical "
            "authentication issue."
        ),
        "missing_info": ["Browser version", "Expected behavior"],
    }

    now = datetime.utcnow()

    instance = BugAnalysis(
        title=payload.title,
        description=payload.description,
        environment=payload.environment,
        severity=mock_result["severity"],
        priority=mock_result["priority"],
        component=mock_result["component"],
        repro_steps="\n".join(mock_result["repro_steps"]),
        reasoning=mock_result["reasoning"],
        missing_info="\n".join(mock_result["missing_info"]),
        raw_response=mock_result,
        model_version="mock-llama3.2",
        prompt_version="v1",
        latency_ms=1200,
        schema_valid=True,
        created_at=now,
        updated_at=now,
    )

    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    return _to_bug_analysis_response(instance)


@router.get("", response_model=BugAnalysisListResponse)
async def list_bug_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> BugAnalysisListResponse:
    total_stmt: Select[tuple[int]] = select(func.count(BugAnalysis.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    stmt: Select[tuple[BugAnalysis]] = (
        select(BugAnalysis)
        .order_by(BugAnalysis.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows: List[BugAnalysis] = list(result.scalars().all())

    return BugAnalysisListResponse(
        items=[_to_bug_analysis_response(row) for row in rows],
        total=total,
    )


@router.get("/{id}", response_model=BugAnalysisResponse)
async def get_bug_analysis(
    id: UUID, db: AsyncSession = Depends(get_db)
) -> BugAnalysisResponse:
    stmt = select(BugAnalysis).where(BugAnalysis.id == id)
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug analysis not found",
        )

    return _to_bug_analysis_response(instance)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bug_analysis(id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    stmt = select(BugAnalysis).where(BugAnalysis.id == id)
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug analysis not found",
        )

    await db.delete(instance)
    await db.commit()

    return None

