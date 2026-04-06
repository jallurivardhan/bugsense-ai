"""Developer transparency: model info, custom examples stats, benchmarks, failures."""

from collections import Counter
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.db.models import BenchmarkRun, CustomExample
from app.services.ai_service import ai_service
from app.services.custom_examples_service import custom_examples_service

router = APIRouter(prefix="/insights", tags=["insights"])


def _infer_provider_from_model(model_version: str | None) -> str:
    if not model_version:
        return "unknown"
    m = model_version.lower()
    if "gpt" in m or m.startswith("o1") or m.startswith("o3") or "davinci" in m:
        return "openai"
    if "llama" in m or "mixtral" in m or "gemma" in m or "groq" in m:
        return "groq"
    return "ollama"


@router.get("/model-info")
async def get_model_info() -> Dict[str, Any]:
    """Current AI model information."""
    provider_info = ai_service.get_provider_info()
    prov = provider_info.get("provider", "unknown")

    return {
        "provider": prov,
        "model": provider_info.get("model", "unknown"),
        "speed": provider_info.get("speed", "unknown"),
        "privacy": provider_info.get("privacy", "unknown"),
        "accuracy": provider_info.get("accuracy", "unknown"),
        "avg_latency_seconds": provider_info.get("avg_latency_seconds", 0),
        "available_providers": [
            {
                "id": "openai",
                "name": "OpenAI GPT-4o",
                "available": bool(settings.OPENAI_API_KEY),
            },
            {"id": "groq", "name": "Groq LLaMA", "available": bool(settings.GROQ_API_KEY)},
            {"id": "ollama", "name": "Ollama Local", "available": True},
        ],
        "context_window": 128000 if prov == "openai" else 8192,
        "temperature": 0.1,
        "max_tokens": 4096,
    }


@router.get("/training-data")
async def get_training_data(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Custom few-shot examples statistics (not model training data)."""
    examples = custom_examples_service.get_examples()

    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    priority_counts = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    domains: Dict[str, int] = {}

    for ex in examples:
        sev = ex.get("severity", "Unknown")
        pri = ex.get("priority", "Unknown")
        domain = ex.get("domain") or "general"

        if sev in severity_counts:
            severity_counts[sev] += 1
        if pri in priority_counts:
            priority_counts[pri] += 1
        domains[domain] = domains.get(domain, 0) + 1

    recent_rows: List[CustomExample] = []
    try:
        result = await db.execute(
            select(CustomExample)
            .where(CustomExample.is_active.is_(True))
            .order_by(desc(CustomExample.created_at))
            .limit(10)
        )
        recent_rows = list(result.scalars().all())
    except Exception as exc:
        print(f"Error loading recent custom examples: {exc}")

    recent_list = [
        {
            "id": str(r.id),
            "title": r.title,
            "description": r.description,
            "severity": r.severity,
            "priority": r.priority,
            "reasoning": r.reasoning,
            "domain": r.domain,
        }
        for r in recent_rows
    ]

    return {
        "total_examples": len(examples),
        "severity_distribution": severity_counts,
        "priority_distribution": priority_counts,
        "domains": domains,
        "examples": recent_list,
    }


@router.get("/evaluation-metrics")
async def get_evaluation_metrics(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Benchmark evaluation metrics over time (stored benchmark runs)."""
    try:
        result = await db.execute(
            select(BenchmarkRun).order_by(desc(BenchmarkRun.created_at)).limit(10)
        )
        runs = list(result.scalars().all())

        history: List[Dict[str, Any]] = []
        for run in reversed(runs):
            mv = run.model_version
            provider = _infer_provider_from_model(mv)
            history.append(
                {
                    "id": str(run.id),
                    "date": run.created_at.isoformat() if run.created_at else None,
                    "provider": provider,
                    "model_version": mv,
                    "total_cases": run.total_tests or 0,
                    "passed": run.passed_tests or 0,
                    "failed": run.failed_tests or 0,
                    "severity_accuracy": float(run.severity_accuracy or 0),
                    "priority_accuracy": float(run.priority_accuracy or 0),
                    "avg_latency": (run.avg_latency_ms or 0) / 1000.0,
                }
            )

        if runs:
            best_accuracy = max((r.severity_accuracy or 0) for r in runs)
            avg_accuracy = sum((r.severity_accuracy or 0) for r in runs) / len(runs)
            total_runs = len(runs)
            latest_run = history[-1] if history else None
        else:
            best_accuracy = 0.0
            avg_accuracy = 0.0
            total_runs = 0
            latest_run = None

        return {
            "total_runs": total_runs,
            "best_accuracy": round(best_accuracy, 1),
            "avg_accuracy": round(avg_accuracy, 1),
            "latest_run": latest_run,
            "history": history,
        }
    except Exception as e:
        print(f"Error fetching evaluation metrics: {e}")
        return {
            "total_runs": 0,
            "best_accuracy": 0.0,
            "avg_accuracy": 0.0,
            "latest_run": None,
            "history": [],
        }


@router.get("/failure-analysis")
async def get_failure_analysis(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Analyze failure patterns from the latest benchmark run JSON results."""
    try:
        run_result = await db.execute(
            select(BenchmarkRun).order_by(desc(BenchmarkRun.created_at)).limit(1)
        )
        latest_run = run_result.scalar_one_or_none()

        if not latest_run:
            return {
                "total_failures": 0,
                "failure_patterns": [],
                "failed_cases": [],
                "recommendations": [
                    "Run a benchmark first to see failure analysis.",
                ],
            }

        raw_results = latest_run.results
        if raw_results is None or not isinstance(raw_results, list):
            raw_results = []

        failed_results = [
            r
            for r in raw_results
            if isinstance(r, dict) and not r.get("passed", False)
        ]

        if not failed_results:
            return {
                "total_failures": 0,
                "failure_patterns": [],
                "failed_cases": [],
                "recommendations": [
                    "No failed test cases in the latest benchmark run.",
                ],
            }

        patterns: Counter[str] = Counter()
        failed_cases: List[Dict[str, Any]] = []

        for r in failed_results:
            exp_sev = (r.get("expected_severity") or "") or ""
            act_sev = (r.get("actual_severity") or "") or "—"
            pattern = f"{exp_sev}->{act_sev}"
            patterns[pattern] += 1

        for r in failed_results[:20]:
            exp_sev = (r.get("expected_severity") or "") or ""
            act_sev = (r.get("actual_severity") or "") or "—"
            failed_cases.append(
                {
                    "test_case": r.get("test_case_name")
                    or r.get("test_case_id")
                    or "—",
                    "expected_severity": exp_sev,
                    "actual_severity": act_sev,
                    "expected_priority": r.get("expected_priority") or "",
                    "actual_priority": r.get("actual_priority") or "",
                }
            )

        failure_patterns = [
            {"pattern": k, "count": v}
            for k, v in patterns.most_common(10)
            if v > 0
        ][:5]

        recommendations: List[str] = []
        if failure_patterns:
            joined = " ".join(p["pattern"] for p in failure_patterns)
            if "->High" in joined or "->Critical" in joined:
                recommendations.append(
                    "AI tends to over-rate severity. Add more Medium/Low examples."
                )
            if "->Low" in joined or "->Medium" in joined:
                recommendations.append(
                    "AI tends to under-rate severity. Add more Critical/High examples."
                )
        if not recommendations:
            recommendations.append(
                "Classification is balanced. Consider adding domain-specific examples."
            )

        return {
            "total_failures": len(failed_results),
            "failure_patterns": failure_patterns,
            "failed_cases": failed_cases[:20],
            "recommendations": recommendations,
        }
    except Exception as e:
        print(f"Error in failure analysis: {e}")
        return {
            "total_failures": 0,
            "failure_patterns": [],
            "failed_cases": [],
            "recommendations": ["Run a benchmark first to see failure analysis."],
        }


@router.get("/decision-trace/{result_id}")
async def get_decision_trace(result_id: str) -> Dict[str, Any]:
    """High-level pipeline steps for transparency (not a stored per-request trace yet)."""
    return {
        "result_id": result_id,
        "steps": [
            {"step": 1, "action": "Parse bug title and description"},
            {"step": 2, "action": "Match against custom examples"},
            {"step": 3, "action": "Apply severity classification rules"},
            {"step": 4, "action": "Determine priority based on impact"},
            {"step": 5, "action": "Generate final classification"},
        ],
        "matched_examples": [],
        "confidence": 0.85,
    }
