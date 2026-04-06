import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.services.ai_service import ai_service


@dataclass
class ExtractedBug:
    """A bug extracted from uploaded file."""

    title: str
    description: str
    raw_severity: str
    raw_priority: str
    normalized_severity: str
    normalized_priority: str
    component: Optional[str] = None
    environment: Optional[str] = None
    confidence: float = 0.0
    source_text: str = ""

    def to_test_case(self) -> Dict[str, Any]:
        """Convert to benchmark test case format."""
        return {
            "title": self.title,
            "description": self.description,
            "environment": self.environment or "Production",
            "expected_severity": self.normalized_severity,
            "expected_priority": self.normalized_priority,
            "expected_component": self.component,
        }


class SeverityNormalizer:
    """Normalizes different severity naming conventions to standard format."""

    SEVERITY_MAP = {
        "critical": "Critical",
        "blocker": "Critical",
        "showstopper": "Critical",
        "p1": "Critical",
        "priority 1": "Critical",
        "highest": "Critical",
        "urgent": "Critical",
        "emergency": "Critical",
        "fatal": "Critical",
        "1": "Critical",
        "sev1": "Critical",
        "sev-1": "Critical",
        "s1": "Critical",
        "high": "High",
        "major": "High",
        "p2": "High",
        "priority 2": "High",
        "important": "High",
        "severe": "High",
        "2": "High",
        "sev2": "High",
        "sev-2": "High",
        "s2": "High",
        "medium": "Medium",
        "moderate": "Medium",
        "normal": "Medium",
        "p3": "Medium",
        "priority 3": "Medium",
        "average": "Medium",
        "3": "Medium",
        "sev3": "Medium",
        "sev-3": "Medium",
        "s3": "Medium",
        "minor": "Medium",
        "low": "Low",
        "trivial": "Low",
        "cosmetic": "Low",
        "p4": "Low",
        "priority 4": "Low",
        "lowest": "Low",
        "4": "Low",
        "sev4": "Low",
        "sev-4": "Low",
        "s4": "Low",
        "enhancement": "Low",
        "wish": "Low",
    }

    PRIORITY_MAP = {
        "p1": "P1",
        "1": "P1",
        "highest": "P1",
        "critical": "P1",
        "blocker": "P1",
        "immediate": "P1",
        "urgent": "P1",
        "p2": "P2",
        "2": "P2",
        "high": "P2",
        "major": "P2",
        "p3": "P3",
        "3": "P3",
        "medium": "P3",
        "normal": "P3",
        "moderate": "P3",
        "p4": "P4",
        "4": "P4",
        "low": "P4",
        "minor": "P4",
        "trivial": "P4",
        "lowest": "P4",
    }

    @classmethod
    def normalize_severity(cls, raw: str) -> str:
        """Convert any severity format to Critical/High/Medium/Low."""
        if not raw:
            return "Medium"
        normalized = raw.lower().strip()
        return cls.SEVERITY_MAP.get(normalized, "Medium")

    @classmethod
    def normalize_priority(cls, raw: str) -> str:
        """Convert any priority format to P1/P2/P3/P4."""
        if not raw:
            return "P3"
        normalized = raw.lower().strip()
        return cls.PRIORITY_MAP.get(normalized, "P3")


class BugExtractorService:
    """AI-powered service to extract bugs from any text content."""

    EXTRACTION_PROMPT = """You are a bug extraction expert. Analyze the following text and extract all bug reports or issues mentioned.

For EACH bug found, extract:
1. title: A short summary of the bug
2. description: Detailed description of the issue
3. severity: The severity level (look for words like Critical, High, Medium, Low, Blocker, Major, Minor, Trivial, or numbered priorities)
4. priority: The priority level (look for P1, P2, P3, P4 or similar)
5. component: The system component affected (e.g., Payment, Login, Search, UI)
6. environment: Where the bug occurs (e.g., Production, Staging, Chrome, iOS)

TEXT TO ANALYZE:
{text}

Respond with a JSON array of bugs. Each bug should have these fields:
{{
    "bugs": [
        {{
            "title": "Short bug title",
            "description": "Full description",
            "severity": "Original severity value found",
            "priority": "Original priority value found",
            "component": "Component name or null",
            "environment": "Environment or null",
            "confidence": 0.95
        }}
    ]
}}

If no bugs are found, return: {{"bugs": []}}

IMPORTANT:
- Extract ALL bugs you can find
- Keep original severity/priority values as found in text
- Set confidence between 0 and 1 based on how clear the bug info is
- If a field is not mentioned, use null
- Return ONLY valid JSON, no other text"""

    def __init__(self) -> None:
        self.ai = ai_service
        self.normalizer = SeverityNormalizer()

    def extract_bugs_from_text(
        self, text: str, source_name: str = "uploaded file"
    ) -> List[ExtractedBug]:
        """Extract bugs from any text content using AI."""
        if not text or len(text.strip()) < 10:
            return []

        max_chars = 15000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]..."

        prompt = self.EXTRACTION_PROMPT.format(text=text)

        try:
            response = self.ai.generate(prompt)

            if not response.get("success"):
                print(f"AI extraction failed: {response.get('error')}")
                return []

            data = response.get("data")
            if data is None:
                raw = response.get("raw") or "{}"
                try:
                    data = json.loads(raw) if isinstance(raw, str) else {}
                except json.JSONDecodeError:
                    json_match = re.search(r"\{[\s\S]*\}", str(raw))
                    if json_match:
                        data = json.loads(json_match.group())
                    else:
                        print("Failed to parse AI response as JSON")
                        return []
                if not isinstance(data, dict):
                    return []

            bugs = data.get("bugs", [])
            if not isinstance(bugs, list):
                return []

            extracted: List[ExtractedBug] = []
            for bug in bugs:
                if not isinstance(bug, dict):
                    continue
                raw_severity = bug.get("severity", "Medium") or "Medium"
                raw_priority = bug.get("priority", "P3") or "P3"
                if isinstance(raw_severity, str):
                    raw_severity = raw_severity.strip() or "Medium"
                if isinstance(raw_priority, str):
                    raw_priority = raw_priority.strip() or "P3"
                else:
                    raw_priority = str(raw_priority)

                comp = bug.get("component")
                env = bug.get("environment")
                extracted.append(
                    ExtractedBug(
                        title=(bug.get("title") or "Untitled Bug").strip()
                        if isinstance(bug.get("title"), str)
                        else "Untitled Bug",
                        description=str(bug.get("description", "") or ""),
                        raw_severity=str(raw_severity),
                        raw_priority=str(raw_priority),
                        normalized_severity=self.normalizer.normalize_severity(
                            str(raw_severity)
                        ),
                        normalized_priority=self.normalizer.normalize_priority(
                            str(raw_priority)
                        ),
                        component=str(comp).strip() if comp else None,
                        environment=str(env).strip() if env else None,
                        confidence=float(bug.get("confidence", 0.5) or 0.5),
                        source_text=source_name,
                    )
                )

            return extracted

        except Exception as e:
            print(f"Bug extraction error: {e}")
            return []

    def extract_from_structured_data(
        self,
        rows: List[Dict[str, Any]],
        field_mapping: Optional[Dict[str, List[str]]] = None,
    ) -> List[ExtractedBug]:
        """Extract bugs from structured data (CSV, Excel rows) with auto-detection."""
        if not rows:
            return []

        if not field_mapping:
            field_mapping = self._auto_detect_fields(rows[0].keys())

        extracted: List[ExtractedBug] = []
        for row in rows:
            title = self._get_field_value(row, field_mapping.get("title", []))
            description = self._get_field_value(
                row, field_mapping.get("description", [])
            )
            severity = self._get_field_value(
                row, field_mapping.get("severity", [])
            )
            priority = self._get_field_value(
                row, field_mapping.get("priority", [])
            )
            component = self._get_field_value(
                row, field_mapping.get("component", [])
            )
            environment = self._get_field_value(
                row, field_mapping.get("environment", [])
            )

            if not title and not description:
                continue

            extracted.append(
                ExtractedBug(
                    title=title or (description[:100] if description else "Untitled"),
                    description=description or title or "",
                    raw_severity=severity or "Medium",
                    raw_priority=priority or "P3",
                    normalized_severity=self.normalizer.normalize_severity(
                        severity or "Medium"
                    ),
                    normalized_priority=self.normalizer.normalize_priority(
                        priority or "P3"
                    ),
                    component=component,
                    environment=environment,
                    confidence=0.9 if title and severity else 0.7,
                    source_text="structured_data",
                )
            )

        return extracted

    def _auto_detect_fields(self, columns: Any) -> Dict[str, List[str]]:
        """Auto-detect which columns map to which bug fields."""
        columns_lower = [str(c).lower() for c in columns]

        mapping: Dict[str, List[str]] = {
            "title": [],
            "description": [],
            "severity": [],
            "priority": [],
            "component": [],
            "environment": [],
        }

        title_keywords = [
            "title",
            "summary",
            "name",
            "subject",
            "issue",
            "bug",
            "defect",
            "problem",
        ]
        for col in columns_lower:
            if any(kw in col for kw in title_keywords):
                mapping["title"].append(col)

        desc_keywords = [
            "description",
            "desc",
            "detail",
            "body",
            "content",
            "steps",
            "notes",
            "comment",
        ]
        for col in columns_lower:
            if any(kw in col for kw in desc_keywords):
                mapping["description"].append(col)

        sev_keywords = ["severity", "sev", "impact", "level", "criticality"]
        for col in columns_lower:
            if any(kw in col for kw in sev_keywords):
                mapping["severity"].append(col)

        pri_keywords = ["priority", "pri", "prio", "urgency", "importance"]
        for col in columns_lower:
            if any(kw in col for kw in pri_keywords):
                mapping["priority"].append(col)

        comp_keywords = [
            "component",
            "module",
            "area",
            "system",
            "feature",
            "category",
            "type",
        ]
        for col in columns_lower:
            if any(kw in col for kw in comp_keywords):
                mapping["component"].append(col)

        env_keywords = ["environment", "env", "platform", "browser", "os", "device"]
        for col in columns_lower:
            if any(kw in col for kw in env_keywords):
                mapping["environment"].append(col)

        return mapping

    def _get_field_value(
        self, row: Dict[str, Any], possible_keys: List[str]
    ) -> Optional[str]:
        """Get value from row trying multiple possible key names."""
        for key in possible_keys:
            if key in row and row[key] not in (None, ""):
                return str(row[key]).strip()
            for actual_key in row.keys():
                if str(actual_key).lower() == key and row[actual_key] not in (
                    None,
                    "",
                ):
                    return str(row[actual_key]).strip()
        return None


bug_extractor = BugExtractorService()
