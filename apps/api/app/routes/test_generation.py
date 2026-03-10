from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.db.models import TestGeneration
from app.schemas import (
    TestCase,
    TestGenerationCreate,
    TestGenerationListResponse,
    TestGenerationResponse,
)
from app.services.test_generator import test_generator

router = APIRouter()


def _to_test_generation_response(model: TestGeneration) -> TestGenerationResponse:
    tests_data = model.generated_tests or []
    tests: List[TestCase] = [TestCase(**item) for item in tests_data]

    return TestGenerationResponse(
        id=model.id,
        requirement=model.requirement,
        include_gherkin=model.include_gherkin,
        tests=tests,
        model_version=model.model_version,
        prompt_version=model.prompt_version,
        latency_ms=model.latency_ms,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("", response_model=TestGenerationResponse, status_code=status.HTTP_201_CREATED)
async def create_test_generation(
    payload: TestGenerationCreate,
    db: AsyncSession = Depends(get_db),
) -> TestGenerationResponse:
    """Generate test cases from a requirement using AI."""

    result = test_generator.generate(
        requirement=payload.requirement,
        include_gherkin=payload.include_gherkin,
    )

    if not result["success"]:
        tests: list[dict] = []
    else:
        tests = result.get("tests", [])

    now = datetime.utcnow()

    instance = TestGeneration(
        requirement=payload.requirement,
        include_gherkin=payload.include_gherkin,
        generated_tests=tests,
        generation_metadata={},
        model_version=result.get("model_version", "unknown"),
        prompt_version=result.get("prompt_version", "v1.0"),
        latency_ms=result.get("latency_ms", 0),
        created_at=now,
        updated_at=now,
    )

    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    return _to_test_generation_response(instance)


@router.get("", response_model=TestGenerationListResponse)
async def list_test_generations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> TestGenerationListResponse:
    total_stmt: Select[tuple[int]] = select(func.count(TestGeneration.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    stmt: Select[tuple[TestGeneration]] = (
        select(TestGeneration)
        .order_by(TestGeneration.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows: List[TestGeneration] = list(result.scalars().all())

    return TestGenerationListResponse(
        items=[_to_test_generation_response(row) for row in rows],
        total=total,
    )


@router.get("/{id}", response_model=TestGenerationResponse)
async def get_test_generation(
    id: UUID, db: AsyncSession = Depends(get_db)
) -> TestGenerationResponse:
    stmt = select(TestGeneration).where(TestGeneration.id == id)
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test generation not found",
        )

    return _to_test_generation_response(instance)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_generation(
    id: UUID, db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(TestGeneration).where(TestGeneration.id == id)
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test generation not found",
        )

    await db.delete(instance)
    await db.commit()

    return None

