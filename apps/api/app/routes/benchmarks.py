import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import BenchmarkRun, get_db
from app.db.models import BenchmarkTestCaseModel
from app.services.benchmark_service import benchmark_service, BenchmarkTestCase
from app.services.custom_examples_service import custom_examples_service
from app.services.bug_extractor import bug_extractor
from app.services.file_processor import file_processor

router = APIRouter()


class BenchmarkRunRequest(BaseModel):
    test_case_ids: Optional[List[str]] = None
    category: Optional[str] = None
    persist_run: bool = True


class RecordBenchmarkSummaryBody(BaseModel):
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    total_tests: int
    passed_tests: int
    failed_tests: int
    avg_latency_ms: float
    schema_valid_rate: float
    severity_accuracy: float
    priority_accuracy: float
    results: List[Dict[str, Any]] = []


async def load_test_cases_from_db(db: AsyncSession) -> List[BenchmarkTestCase]:
    """Load test cases from database."""
    result = await db.execute(select(BenchmarkTestCaseModel))
    db_cases = result.scalars().all()
    
    return [
        BenchmarkTestCase(
            id=tc.id,
            name=tc.name,
            title=tc.title,
            description=tc.description,
            environment=tc.environment,
            expected_severity=tc.expected_severity,
            expected_priority=tc.expected_priority,
            expected_component=tc.expected_component,
            category=tc.category,
        )
        for tc in db_cases
    ]


@router.get("/test-cases")
async def get_test_cases(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get available benchmark test cases."""
    # First try to load from database
    db_test_cases = await load_test_cases_from_db(db)
    
    if db_test_cases:
        # Use database test cases
        test_cases = db_test_cases
        if category:
            test_cases = [tc for tc in test_cases if tc.category == category]
        # Also sync to in-memory service
        benchmark_service.test_cases = db_test_cases
    else:
        # Fall back to in-memory (defaults)
        test_cases = benchmark_service.get_test_cases(category)
    
    return {
        "items": [
            {
                "id": tc.id,
                "name": tc.name,
                "title": tc.title,
                "description": tc.description,
                "environment": tc.environment,
                "expected_severity": tc.expected_severity,
                "expected_priority": tc.expected_priority,
                "expected_component": tc.expected_component,
                "category": tc.category,
            }
            for tc in test_cases
        ],
        "total": len(test_cases),
    }


@router.post("/run")
async def run_benchmark(
    request: BenchmarkRunRequest,
    sample_size: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Run benchmark on current test cases."""
    try:
        # Load test cases from DB first
        db_test_cases = await load_test_cases_from_db(db)
        if db_test_cases:
            benchmark_service.test_cases = db_test_cases
        
        summary = benchmark_service.run_benchmark(
            test_case_ids=request.test_case_ids,
            category=request.category,
            sample_size=sample_size,
        )

        if not request.persist_run:
            return {
                "id": summary.run_id,
                **summary.to_dict(),
            }

        db_run = BenchmarkRun(
            model_version=summary.model_version,
            prompt_version=summary.prompt_version,
            total_tests=summary.total_tests,
            passed_tests=summary.passed_tests,
            failed_tests=summary.failed_tests,
            avg_latency_ms=summary.avg_latency_ms,
            schema_valid_rate=summary.schema_valid_rate,
            severity_accuracy=summary.severity_accuracy,
            priority_accuracy=summary.priority_accuracy,
            results=summary.results,
        )

        db.add(db_run)
        await db.commit()
        await db.refresh(db_run)

        return {
            "id": str(db_run.id),
            **summary.to_dict(),
        }
    except Exception as e:
        print(f"Benchmark run error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/record-summary")
async def record_benchmark_summary(
    body: RecordBenchmarkSummaryBody,
    db: AsyncSession = Depends(get_db),
):
    """Persist a merged benchmark summary (e.g. after per-test runs from the client)."""
    try:
        db_run = BenchmarkRun(
            model_version=body.model_version or "",
            prompt_version=body.prompt_version or "",
            total_tests=body.total_tests,
            passed_tests=body.passed_tests,
            failed_tests=body.failed_tests,
            avg_latency_ms=body.avg_latency_ms,
            schema_valid_rate=body.schema_valid_rate,
            severity_accuracy=body.severity_accuracy,
            priority_accuracy=body.priority_accuracy,
            results=body.results,
        )
        db.add(db_run)
        await db.commit()
        await db.refresh(db_run)
        return {
            "id": str(db_run.id),
            "model_version": db_run.model_version or "",
            "prompt_version": db_run.prompt_version or "",
            "total_tests": db_run.total_tests or 0,
            "passed_tests": db_run.passed_tests or 0,
            "failed_tests": db_run.failed_tests or 0,
            "avg_latency_ms": db_run.avg_latency_ms or 0,
            "schema_valid_rate": db_run.schema_valid_rate or 0,
            "severity_accuracy": db_run.severity_accuracy or 0,
            "priority_accuracy": db_run.priority_accuracy or 0,
            "results": db_run.results or [],
            "created_at": db_run.created_at.isoformat() if db_run.created_at else "",
        }
    except Exception as e:
        print(f"Record benchmark summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/extract-bugs")
async def extract_bugs_from_file(file: UploadFile = File(...)):
    """Upload any file and extract bugs using AI."""
    try:
        content = await file.read()
        filename = file.filename or "uploaded_file"

        processed = file_processor.process_file(filename, content)

        if processed.error:
            return {
                "success": False,
                "error": processed.error,
                "filename": filename,
                "file_type": processed.file_type,
            }

        extracted_bugs: List[Any] = []

        if processed.structured_data:
            extracted_bugs = bug_extractor.extract_from_structured_data(
                processed.structured_data
            )

        if not extracted_bugs and processed.text_content:
            extracted_bugs = bug_extractor.extract_bugs_from_text(
                processed.text_content,
                source_name=filename,
            )

        return {
            "success": True,
            "filename": filename,
            "file_type": processed.file_type,
            "content_type": processed.content_type,
            "rows_found": processed.row_count,
            "bugs_extracted": len(extracted_bugs),
            "bugs": [
                {
                    "id": f"ext-{i + 1:03d}",
                    "title": bug.title,
                    "description": bug.description,
                    "raw_severity": bug.raw_severity,
                    "raw_priority": bug.raw_priority,
                    "normalized_severity": bug.normalized_severity,
                    "normalized_priority": bug.normalized_priority,
                    "component": bug.component,
                    "environment": bug.environment,
                    "confidence": bug.confidence,
                }
                for i, bug in enumerate(extracted_bugs)
            ],
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filename": getattr(file, "filename", None),
        }


@router.post("/import-extracted-bugs")
async def import_extracted_bugs(
    bugs: List[Dict[str, Any]] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Import extracted bugs as benchmark test cases - persisted to database."""
    try:
        # Clear existing imported test cases from database
        await db.execute(delete(BenchmarkTestCaseModel))
        
        # Insert new test cases
        for i, bug in enumerate(bugs):
            tc = BenchmarkTestCaseModel(
                id=bug.get("id", f"imp-{i + 1:03d}"),
                name=(bug.get("title", "") or "")[:100],
                title=bug.get("title", "Untitled")[:255],
                description=bug.get("description", ""),
                environment=bug.get("environment") or "Production",
                expected_severity=bug.get("normalized_severity", "Medium"),
                expected_priority=bug.get("normalized_priority", "P3"),
                expected_component=bug.get("component"),
                category="imported",
            )
            db.add(tc)
        
        await db.commit()
        
        # Also update in-memory service
        test_cases = []
        for i, bug in enumerate(bugs):
            test_cases.append({
                "id": bug.get("id", f"imp-{i + 1:03d}"),
                "name": (bug.get("title", "") or "")[:50],
                "title": bug.get("title", "Untitled"),
                "description": bug.get("description", ""),
                "environment": bug.get("environment") or "Production",
                "expected_severity": bug.get("normalized_severity", "Medium"),
                "expected_priority": bug.get("normalized_priority", "P3"),
                "expected_component": bug.get("component"),
                "category": "imported",
            })
        benchmark_service.set_custom_test_cases(test_cases)

        return {
            "success": True,
            "imported_count": len(bugs),
            "message": f"Successfully imported {len(bugs)} test cases to database",
        }
    except Exception as e:
        await db.rollback()
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/supported-formats")
async def get_supported_formats():
    """List supported file formats for bug extraction."""
    return {
        "formats": [
            {"extension": ".csv", "name": "CSV", "description": "Comma-separated values"},
            {"extension": ".xlsx", "name": "Excel", "description": "Microsoft Excel spreadsheet"},
            {"extension": ".json", "name": "JSON", "description": "JavaScript Object Notation"},
            {"extension": ".xml", "name": "XML", "description": "XML (including Jira exports)"},
            {"extension": ".pdf", "name": "PDF", "description": "PDF documents"},
            {"extension": ".docx", "name": "Word", "description": "Microsoft Word document"},
            {"extension": ".txt", "name": "Text", "description": "Plain text file"},
            {"extension": ".md", "name": "Markdown", "description": "Markdown file"},
            {"extension": ".log", "name": "Log", "description": "Log file"},
        ],
    }


@router.post("/reset-test-cases")
async def reset_test_cases(db: AsyncSession = Depends(get_db)):
    """Restore default benchmark test cases - clears database."""
    # Clear database
    await db.execute(delete(BenchmarkTestCaseModel))
    await db.commit()
    # Reset in-memory to defaults
    benchmark_service.reset_to_default_test_cases()
    return {"success": True, "message": "Reset to default test cases"}


@router.get("/custom-examples")
async def get_custom_examples():
    """Get all custom few-shot examples."""
    return {"examples": custom_examples_service.get_examples()}


@router.post("/custom-examples")
async def add_custom_example(
    example: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Add a custom few-shot example."""
    required = ["title", "severity", "priority"]
    for field in required:
        if field not in example:
            raise HTTPException(400, f"Missing required field: {field}")

    if example["severity"] not in ["Critical", "High", "Medium", "Low"]:
        raise HTTPException(400, "Severity must be Critical, High, Medium, or Low")

    if example["priority"] not in ["P1", "P2", "P3", "P4"]:
        raise HTTPException(400, "Priority must be P1, P2, P3, or P4")

    result = await custom_examples_service.add_example(db, example)
    return result


@router.delete("/custom-examples/{example_id}")
async def delete_custom_example(
    example_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom example."""
    result = await custom_examples_service.delete_example(db, example_id)
    if not result["success"]:
        err = result.get("error", "Not found")
        if err == "Invalid example id":
            raise HTTPException(status_code=400, detail=err)
        raise HTTPException(status_code=404, detail=err)
    return result


@router.get("")
async def list_benchmark_runs(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List past benchmark runs."""
    try:
        count_result = await db.execute(select(func.count(BenchmarkRun.id)))
        total = count_result.scalar() or 0

        result = await db.execute(
            select(BenchmarkRun)
            .order_by(BenchmarkRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        runs = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(run.id),
                    "model_version": run.model_version or "",
                    "prompt_version": run.prompt_version or "",
                    "total_tests": run.total_tests or 0,
                    "passed_tests": run.passed_tests or 0,
                    "failed_tests": run.failed_tests or 0,
                    "avg_latency_ms": run.avg_latency_ms or 0,
                    "schema_valid_rate": run.schema_valid_rate or 0,
                    "severity_accuracy": run.severity_accuracy or 0,
                    "priority_accuracy": run.priority_accuracy or 0,
                    "created_at": run.created_at.isoformat() if run.created_at else "",
                }
                for run in runs
            ],
            "total": total,
        }
    except Exception as e:
        print(f"Error listing benchmark runs: {e}")
        return {"items": [], "total": 0}


@router.get("/{run_id}")
async def get_benchmark_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific benchmark run."""
    result = await db.execute(
        select(BenchmarkRun).where(BenchmarkRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Benchmark run not found")

    return {
        "id": str(run.id),
        "model_version": run.model_version,
        "prompt_version": run.prompt_version,
        "total_tests": run.total_tests,
        "passed_tests": run.passed_tests,
        "failed_tests": run.failed_tests,
        "avg_latency_ms": run.avg_latency_ms,
        "schema_valid_rate": run.schema_valid_rate,
        "severity_accuracy": run.severity_accuracy,
        "priority_accuracy": run.priority_accuracy,
        "results": run.results or [],
        "created_at": run.created_at.isoformat(),
    }
