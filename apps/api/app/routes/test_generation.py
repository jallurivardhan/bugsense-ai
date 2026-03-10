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


@router.post(
    "",
    response_model=TestGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_generation(
    payload: TestGenerationCreate,
    db: AsyncSession = Depends(get_db),
) -> TestGenerationResponse:
    mock_tests = [
        {
            "name": "Test valid login",
            "steps": [
                "Navigate to login",
                "Enter valid credentials",
                "Click submit",
            ],
            "expected_result": "User is logged in successfully",
            "gherkin": (
                "Given I am on the login page\n"
                "When I enter valid credentials\n"
                "Then I should be logged in"
            ),
        },
        {
            "name": "Test invalid login",
            "steps": [
                "Navigate to login",
                "Enter invalid credentials",
                "Click submit",
            ],
            "expected_result": "Error message is displayed",
            "gherkin": (
                "Given I am on the login page\n"
                "When I enter invalid credentials\n"
                "Then I should see an error message"
            ),
        },
    ]

    now = datetime.utcnow()

    instance = TestGeneration(
        requirement=payload.requirement,
        include_gherkin=payload.include_gherkin,
        generated_tests=mock_tests,
        generation_metadata={"source": "mock"},
        model_version="mock-llama3.2",
        prompt_version="v1",
        latency_ms=900,
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

