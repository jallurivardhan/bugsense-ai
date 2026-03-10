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
from app.services.bug_analyzer import bug_analyzer

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


@router.post("", response_model=BugAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_bug_analysis(
    payload: BugAnalysisCreate,
    db: AsyncSession = Depends(get_db),
) -> BugAnalysisResponse:
    """Analyze a bug report using AI."""

    result = bug_analyzer.analyze(
        title=payload.title,
        description=payload.description,
        environment=payload.environment,
    )

    if not result["success"]:
        severity = None
        priority = None
        component = None
        repro_steps: List[str] = []
        reasoning = f"AI analysis failed: {result.get('error', 'Unknown error')}"
        missing_info: List[str] = []
        raw_response = result.get("raw_response")
        schema_valid = False
    else:
        severity = result.get("severity")
        priority = result.get("priority")
        component = result.get("component")
        repro_steps = result.get("repro_steps", [])
        reasoning = result.get("reasoning")
        missing_info = result.get("missing_info", [])
        raw_response = result.get("raw_response")
        schema_valid = result.get("schema_valid", True)

    instance = BugAnalysis(
        title=payload.title,
        description=payload.description,
        environment=payload.environment,
        severity=severity,
        priority=priority,
        component=component,
        repro_steps="\n".join(repro_steps) if repro_steps else None,
        reasoning=reasoning,
        missing_info="\n".join(missing_info) if missing_info else None,
        raw_response=raw_response,
        model_version=result.get("model_version", "unknown"),
        prompt_version=result.get("prompt_version", "v1.0"),
        latency_ms=result.get("latency_ms", 0),
        schema_valid=schema_valid,
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

