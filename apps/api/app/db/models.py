import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class BugAnalysis(Base):
    __tablename__ = "bug_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(length=500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str | None] = mapped_column(String(length=255), nullable=True)

    # AI output fields
    severity: Mapped[str | None] = mapped_column(String(length=50), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(length=50), nullable=True)
    component: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    repro_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(String(length=100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(length=100), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TestGeneration(Base):
    __tablename__ = "test_generations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    include_gherkin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    generated_tests: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    generation_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    model_version: Mapped[str] = mapped_column(String(length=100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(length=100), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(length=512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(length=50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(length=50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    chunk_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")


class CustomExample(Base):
    """User-defined few-shot examples for bug severity/priority classification."""

    __tablename__ = "custom_examples"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )


class LearnedPatterns(Base):
    """Persisted learned severity/priority patterns for benchmarks (survives restart)."""

    __tablename__ = "learned_patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    severity_examples: Mapped[dict] = mapped_column(JSONB, nullable=False)
    priority_examples: Mapped[dict] = mapped_column(JSONB, nullable=False)
    severity_keywords: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    priority_keywords: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    guidelines: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_bugs_analyzed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_version: Mapped[str | None] = mapped_column(
        String(length=100), nullable=True
    )
    prompt_version: Mapped[str | None] = mapped_column(
        String(length=100), nullable=True
    )
    total_tests: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    passed_tests: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    failed_tests: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    avg_latency_ms: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=0
    )
    schema_valid_rate: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=0
    )
    severity_accuracy: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=0
    )
    priority_accuracy: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=0
    )
    results: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )


class BenchmarkTestCaseModel(Base):
    __tablename__ = "benchmark_test_cases"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(String(100), default="Production")
    expected_severity: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_priority: Mapped[str] = mapped_column(String(10), nullable=False)
    expected_component: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="imported")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=True
    )
