import random
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.bug_analyzer import bug_analyzer


@dataclass
class BenchmarkTestCase:
    """A single test case for benchmarking."""

    id: str
    name: str
    title: str
    description: str
    environment: str
    expected_severity: str
    expected_priority: str
    expected_component: Optional[str] = None
    category: str = "general"


@dataclass
class BenchmarkResult:
    """Result of running a single test case."""

    test_case_id: str
    test_case_name: str
    passed: bool
    latency_ms: float
    schema_valid: bool
    severity_match: bool
    priority_match: bool
    component_match: bool
    expected_severity: str
    actual_severity: Optional[str]
    expected_priority: str
    actual_priority: Optional[str]
    expected_component: Optional[str]
    actual_component: Optional[str]
    error: Optional[str] = None


@dataclass
class BenchmarkRunSummary:
    """Summary of a complete benchmark run."""

    run_id: str
    model_version: str
    prompt_version: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    avg_latency_ms: float
    schema_valid_rate: float
    severity_accuracy: float
    priority_accuracy: float
    component_accuracy: float
    started_at: str
    completed_at: str
    duration_seconds: float
    results: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BenchmarkService:
    """Service for running AI model benchmarks."""

    def __init__(self) -> None:
        self.test_cases = self._create_default_test_cases()

    def _create_default_test_cases(self) -> List[BenchmarkTestCase]:
        """Create default benchmark test cases."""
        return [
            BenchmarkTestCase(
                id="tc-001",
                name="Payment System Down",
                title="Payment processing completely broken",
                description="No customers can complete purchases. All payment attempts fail with error 500. Revenue is zero since 2am.",
                environment="Production",
                expected_severity="Critical",
                expected_priority="P1",
                expected_component="Payment",
                category="general",
            ),
            BenchmarkTestCase(
                id="tc-002",
                name="Database Connection Lost",
                title="Application cannot connect to database",
                description="All API endpoints returning 503. Database connection pool exhausted. Users see 'Service Unavailable' on all pages.",
                environment="Production",
                expected_severity="Critical",
                expected_priority="P1",
                expected_component="Database",
                category="general",
            ),
            BenchmarkTestCase(
                id="tc-003",
                name="Login Failure",
                title="Users cannot log in with correct credentials",
                description="Multiple users reporting they cannot log in even with correct password. Password reset emails not being sent. Started after last deployment.",
                environment="Production, Chrome",
                expected_severity="High",
                expected_priority="P1",
                expected_component="Authentication",
                category="general",
            ),
            BenchmarkTestCase(
                id="tc-004",
                name="Data Loss on Save",
                title="Form data lost when saving",
                description="Users fill out long forms but data is not saved. Clicking Save shows success but data is gone on refresh. Affects the registration form.",
                environment="Safari, iOS",
                expected_severity="High",
                expected_priority="P2",
                expected_component="Form",
                category="general",
            ),
            BenchmarkTestCase(
                id="tc-005",
                name="Slow Search",
                title="Search takes 30 seconds to return results",
                description="Product search is extremely slow. Users waiting 30+ seconds for results. Search eventually works but UX is terrible.",
                environment="All browsers",
                expected_severity="Medium",
                expected_priority="P2",
                expected_component="Search",
                category="general",
            ),
            BenchmarkTestCase(
                id="tc-006",
                name="Email Formatting",
                title="Order confirmation emails have broken formatting",
                description="Order confirmation emails show HTML tags instead of formatted text. Links work but email looks unprofessional.",
                environment="Gmail, Outlook",
                expected_severity="Medium",
                expected_priority="P3",
                expected_component="Email",
                category="general",
            ),
            BenchmarkTestCase(
                id="tc-007",
                name="Typo in UI",
                title="Spelling mistake on checkout page",
                description="The word 'Reciept' is spelled incorrectly. Should be 'Receipt'. Appears on the order confirmation page.",
                environment="All",
                expected_severity="Low",
                expected_priority="P4",
                expected_component="UI",
                category="general",
            ),
            BenchmarkTestCase(
                id="tc-008",
                name="Wrong Copyright Year",
                title="Footer shows 2023 instead of 2024",
                description="Copyright year in footer is outdated. Shows 2023 but should show 2024. Visible on all pages.",
                environment="All",
                expected_severity="Low",
                expected_priority="P4",
                expected_component="UI",
                category="general",
            ),
            BenchmarkTestCase(
                id="tc-009",
                name="Unicode in Input",
                title="App crashes with emoji in username",
                description="When user enters emoji 😀 in username field, the form submission fails silently. No error shown.",
                environment="Chrome, Windows",
                expected_severity="Medium",
                expected_priority="P3",
                expected_component="Validation",
                category="edge_case",
            ),
            BenchmarkTestCase(
                id="tc-010",
                name="Empty State Bug",
                title="Error when cart is empty",
                description="Clicking checkout with empty cart shows JavaScript error instead of friendly message.",
                environment="Firefox",
                expected_severity="Medium",
                expected_priority="P3",
                expected_component="Cart",
                category="edge_case",
            ),
        ]

    def get_test_cases(
        self,
        category: Optional[str] = None,
    ) -> List[BenchmarkTestCase]:
        """Get test cases, optionally filtered by category."""
        if category:
            return [tc for tc in self.test_cases if tc.category == category]
        return self.test_cases

    def reset_to_default_test_cases(self) -> None:
        """Restore the built-in benchmark suite."""
        self.test_cases = self._create_default_test_cases()

    def set_custom_test_cases(self, raw_cases: List[Dict[str, Any]]) -> None:
        """Replace the active suite with imported or custom test cases."""
        cases: List[BenchmarkTestCase] = []
        for i, tc in enumerate(raw_cases):
            title = str(tc.get("title", "Untitled"))
            name = str(tc.get("name", "")).strip() or (title[:50] if title else f"Case {i + 1}")
            cases.append(
                BenchmarkTestCase(
                    id=str(tc.get("id", f"imp-{i + 1:03d}")),
                    name=name[:50],
                    title=title,
                    description=str(tc.get("description", "")),
                    environment=str(tc.get("environment") or "Production"),
                    expected_severity=str(tc.get("expected_severity", "Medium")),
                    expected_priority=str(tc.get("expected_priority", "P3")),
                    expected_component=tc.get("expected_component"),
                    category=str(tc.get("category", "imported")),
                )
            )
        self.test_cases = cases

    def run_single_test(
        self,
        test_case: BenchmarkTestCase,
    ) -> BenchmarkResult:
        """Run a single benchmark test case."""
        start_time = time.time()

        try:
            result = bug_analyzer.analyze(
                title=test_case.title,
                description=test_case.description,
                environment=test_case.environment,
            )

            latency_ms = (time.time() - start_time) * 1000

            if not result.get("success"):
                return BenchmarkResult(
                    test_case_id=test_case.id,
                    test_case_name=test_case.name,
                    passed=False,
                    latency_ms=latency_ms,
                    schema_valid=False,
                    severity_match=False,
                    priority_match=False,
                    component_match=False,
                    expected_severity=test_case.expected_severity,
                    actual_severity=None,
                    expected_priority=test_case.expected_priority,
                    actual_priority=None,
                    expected_component=test_case.expected_component,
                    actual_component=None,
                    error=result.get("error", "Unknown error"),
                )

            actual_severity = result.get("severity")
            actual_priority = result.get("priority")
            actual_component = result.get("component")

            severity_match = (
                actual_severity is not None
                and actual_severity.lower()
                == test_case.expected_severity.lower()
            )
            priority_match = (
                actual_priority is not None
                and actual_priority.upper()
                == test_case.expected_priority.upper()
            )

            component_match = False
            if test_case.expected_component and actual_component:
                exp_lower = test_case.expected_component.lower()
                act_lower = actual_component.lower()
                component_match = exp_lower in act_lower or act_lower in exp_lower

            passed = severity_match and priority_match

            return BenchmarkResult(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                passed=passed,
                latency_ms=latency_ms,
                schema_valid=result.get("schema_valid", False),
                severity_match=severity_match,
                priority_match=priority_match,
                component_match=component_match,
                expected_severity=test_case.expected_severity,
                actual_severity=actual_severity,
                expected_priority=test_case.expected_priority,
                actual_priority=actual_priority,
                expected_component=test_case.expected_component,
                actual_component=actual_component,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return BenchmarkResult(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                passed=False,
                latency_ms=latency_ms,
                schema_valid=False,
                severity_match=False,
                priority_match=False,
                component_match=False,
                expected_severity=test_case.expected_severity,
                actual_severity=None,
                expected_priority=test_case.expected_priority,
                actual_priority=None,
                expected_component=test_case.expected_component,
                actual_component=None,
                error=str(e),
            )

    def run_benchmark(
        self,
        test_case_ids: Optional[List[str]] = None,
        category: Optional[str] = None,
        sample_size: Optional[int] = None,
    ) -> BenchmarkRunSummary:
        """Run a complete benchmark suite, optionally sampling a subset for quick demos."""
        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        if test_case_ids:
            test_cases = [
                tc for tc in self.test_cases if tc.id in test_case_ids
            ]
        elif category:
            test_cases = self.get_test_cases(category)
        else:
            test_cases = list(self.test_cases)

        if sample_size and sample_size < len(test_cases):
            test_cases_to_run = random.sample(test_cases, sample_size)
            print(
                f"Starting benchmark run {run_id} with {len(test_cases_to_run)} "
                f"sampled test cases (from {len(test_cases)} total)..."
            )
        else:
            test_cases_to_run = test_cases
            print(
                f"Starting benchmark run {run_id} with {len(test_cases_to_run)} test cases..."
            )

        results: List[BenchmarkResult] = []
        for i, tc in enumerate(test_cases_to_run, 1):
            print(f"  Running test {i}/{len(test_cases_to_run)}: {tc.name}...")
            result = self.run_single_test(tc)
            results.append(result)
            print(
                f"  Completed: {'PASS' if result.passed else 'FAIL'} "
                f"(Severity: {result.actual_severity}, Expected: {result.expected_severity})"
            )

        completed_at = datetime.utcnow()

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests

        latencies = [r.latency_ms for r in results]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        schema_valid_count = sum(1 for r in results if r.schema_valid)
        severity_match_count = sum(1 for r in results if r.severity_match)
        priority_match_count = sum(1 for r in results if r.priority_match)
        component_match_count = sum(1 for r in results if r.component_match)

        if total_tests:
            sev_pct = severity_match_count / total_tests * 100
            print(
                f"Benchmark complete! Passed: {passed_tests}/{total_tests}, "
                f"Severity Accuracy: {sev_pct:.1f}%"
            )
        else:
            print(
                f"Benchmark complete! Passed: {passed_tests}/{total_tests}, "
                "no test cases run."
            )

        return BenchmarkRunSummary(
            run_id=run_id,
            model_version=bug_analyzer.ai.model,
            prompt_version=bug_analyzer.prompt_version,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            avg_latency_ms=round(avg_latency, 2),
            schema_valid_rate=round(
                schema_valid_count / total_tests * 100, 1
            )
            if total_tests
            else 0,
            severity_accuracy=round(
                severity_match_count / total_tests * 100, 1
            )
            if total_tests
            else 0,
            priority_accuracy=round(
                priority_match_count / total_tests * 100, 1
            )
            if total_tests
            else 0,
            component_accuracy=round(
                component_match_count / total_tests * 100, 1
            )
            if total_tests
            else 0,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_seconds=round(
                (completed_at - started_at).total_seconds(), 2
            ),
            results=[asdict(r) for r in results],
        )


benchmark_service = BenchmarkService()
