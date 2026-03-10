from typing import Any, Dict

from app.services.ai_service import ai_service
from app.services.prompts import (
    TEST_GENERATION_SYSTEM_PROMPT,
    TEST_GENERATION_USER_PROMPT,
)


class TestGenerator:
    def __init__(self) -> None:
        self.ai = ai_service
        self.prompt_version = "v1.0"

    def generate(
        self,
        requirement: str,
        include_gherkin: bool = False,
    ) -> Dict[str, Any]:
        """Generate test cases from a requirement."""
        prompt = TEST_GENERATION_USER_PROMPT.format(
            requirement=requirement,
            include_gherkin="Yes" if include_gherkin else "No",
        )

        result = self.ai.generate(prompt, TEST_GENERATION_SYSTEM_PROMPT)

        if result["success"]:
            data = result["data"]
            tests = data.get("tests", [])

            if not include_gherkin:
                for test in tests:
                    test.pop("gherkin", None)

            return {
                "success": True,
                "tests": tests,
                "raw_response": result["data"],
                "latency_ms": result["latency_ms"],
                "model_version": result["model"],
                "prompt_version": self.prompt_version,
            }

        return {
            "success": False,
            "error": result.get("error"),
            "raw_response": result.get("raw"),
            "latency_ms": result["latency_ms"],
            "model_version": result["model"],
            "prompt_version": self.prompt_version,
        }


test_generator = TestGenerator()

