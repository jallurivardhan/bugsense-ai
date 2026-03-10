from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BugAnalysisCreate(BaseModel):
  title: str = Field(..., min_length=1, max_length=500)
  description: str = Field(..., min_length=1)
  environment: Optional[str] = None


class BugAnalysisResult(BaseModel):
  severity: Optional[str] = None
  priority: Optional[str] = None
  component: Optional[str] = None
  repro_steps: Optional[List[str]] = None
  reasoning: Optional[str] = None
  missing_info: Optional[List[str]] = None


class BugAnalysisResponse(BaseModel):
  id: UUID
  title: str
  description: str
  environment: Optional[str]
  result: BugAnalysisResult
  model_version: str
  prompt_version: str
  latency_ms: int
  schema_valid: bool
  created_at: datetime

  model_config = {
    "from_attributes": True,
    "protected_namespaces": (),
  }


class BugAnalysisListResponse(BaseModel):
  items: List[BugAnalysisResponse]
  total: int

