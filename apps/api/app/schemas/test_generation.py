from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TestGenerationCreate(BaseModel):
    requirement: str = Field(..., min_length=1)
    include_gherkin: bool = False


class TestCase(BaseModel):
    name: str
    steps: List[str]
    expected_result: str
    gherkin: Optional[str] = None


class TestGenerationResponse(BaseModel):
    id: UUID
    requirement: str
    include_gherkin: bool
    tests: List[TestCase]
    metadata: Optional[Dict[str, Any]] = None
    model_version: str
    prompt_version: str
    latency_ms: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
    }


class TestGenerationListResponse(BaseModel):
    items: List[TestGenerationResponse]
    total: int

