"""Aggregated dashboard statistics."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.db.models import BenchmarkRun, BugAnalysis, Document
from app.services.ai_service import ai_service
from app.services.custom_examples_service import custom_examples_service

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Bug analyses, documents, benchmarks, provider, and custom examples."""
    total_analyses_result = await db.execute(
        select(func.count()).select_from(BugAnalysis)
    )
    total_analyses = int(total_analyses_result.scalar() or 0)

    avg_lat_result = await db.execute(select(func.avg(BugAnalysis.latency_ms)))
    avg_latency_ms = avg_lat_result.scalar()
    avg_latency = (
        float(avg_latency_ms) / 1000.0 if avg_latency_ms is not None else 0.0
    )

    valid_count_result = await db.execute(
        select(func.count())
        .select_from(BugAnalysis)
        .where(BugAnalysis.schema_valid.is_(True))
    )
    valid_count = int(valid_count_result.scalar() or 0)
    schema_valid_rate = (
        (valid_count / total_analyses * 100.0) if total_analyses else 0.0
    )

    indexed_result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(Document.status == "indexed")
    )
    indexed_documents = int(indexed_result.scalar() or 0)

    recent_analyses_result = await db.execute(
        select(BugAnalysis).order_by(desc(BugAnalysis.created_at)).limit(5)
    )
    recent_rows = recent_analyses_result.scalars().all()
    recent_analyses: List[Dict[str, Any]] = [
        {
            "id": str(r.id),
            "title": r.title,
            "severity": r.severity,
            "priority": r.priority,
            "component": r.component,
            "latency_ms": r.latency_ms,
            "schema_valid": r.schema_valid,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_rows
    ]

    total_bench_result = await db.execute(
        select(func.count()).select_from(BenchmarkRun)
    )
    total_benchmark_runs = int(total_bench_result.scalar() or 0)

    best_acc_result = await db.execute(
        select(func.max(BenchmarkRun.severity_accuracy))
    )
    best_accuracy = float(best_acc_result.scalar() or 0)

    benchmark_result = await db.execute(
        select(BenchmarkRun).order_by(desc(BenchmarkRun.created_at)).limit(5)
    )
    recent_benchmarks = list(benchmark_result.scalars().all())

    recent_benchmarks_payload = [
        {
            "id": str(r.id),
            "severity_accuracy": float(r.severity_accuracy or 0),
            "priority_accuracy": float(r.priority_accuracy or 0),
            "total_tests": r.total_tests or 0,
            "passed": r.passed_tests or 0,
            "provider": r.model_version or "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_benchmarks
    ]

    provider_info = ai_service.get_provider_info()
    examples_count = len(custom_examples_service.get_examples())

    return {
        "total_analyses": total_analyses,
        "avg_latency": round(avg_latency, 3),
        "schema_valid_rate": round(schema_valid_rate, 1),
        "indexed_documents": indexed_documents,
        "recent_analyses": recent_analyses,
        "best_accuracy": round(best_accuracy, 1),
        "total_benchmark_runs": total_benchmark_runs,
        "recent_benchmarks": recent_benchmarks_payload,
        "current_provider": provider_info.get("provider", "unknown"),
        "current_model": provider_info.get("model", "unknown"),
        "custom_examples_count": examples_count,
    }
