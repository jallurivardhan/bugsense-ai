from typing import Any, Dict, Optional

from app.services.ai_service import ai_service
from app.services.prompts import (
    BUG_ANALYSIS_SYSTEM_PROMPT,
    BUG_ANALYSIS_USER_PROMPT,
)


class BugAnalyzer:
    def __init__(self) -> None:
        self.ai = ai_service
        self.prompt_version = "v1.0"

    def analyze(
        self,
        title: str,
        description: str,
        environment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze a bug report and return structured triage information."""
        prompt = BUG_ANALYSIS_USER_PROMPT.format(
            title=title,
            description=description,
            environment=environment or "Not specified",
        )

        result = self.ai.generate(prompt, BUG_ANALYSIS_SYSTEM_PROMPT)

        if result["success"]:
            data = result["data"]
            return {
                "success": True,
                "severity": data.get("severity"),
                "priority": data.get("priority"),
                "component": data.get("component"),
                "repro_steps": data.get("repro_steps", []),
                "reasoning": data.get("reasoning"),
                "missing_info": data.get("missing_info", []),
                "raw_response": result["data"],
                "latency_ms": result["latency_ms"],
                "model_version": result["model"],
                "prompt_version": self.prompt_version,
                "schema_valid": True,
            }

        # Error case: return info for logging and downstream handling
        return {
            "success": False,
            "error": result.get("error"),
            "raw_response": result.get("raw"),
            "latency_ms": result["latency_ms"],
            "model_version": result["model"],
            "prompt_version": self.prompt_version,
            "schema_valid": False,
        }


bug_analyzer = BugAnalyzer()

