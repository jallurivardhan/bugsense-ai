from typing import Any, Dict, Optional

from app.services.ai_service import ai_service
from app.services.custom_examples_service import custom_examples_service
from app.services.prompts import (
    BUG_ANALYSIS_SYSTEM_PROMPT,
    BUG_ANALYSIS_USER_PROMPT,
)
from app.services.rag_service import rag_service


class BugAnalyzer:
    def __init__(self) -> None:
        self.ai = ai_service
        self.rag = rag_service
        self.prompt_version = "v1.1-rag"

    def analyze(
        self,
        title: str,
        description: str,
        environment: Optional[str] = None,
        use_rag: bool = True,
    ) -> Dict[str, Any]:
        """Analyze a bug report with optional RAG context."""
        query = f"{title} {description}"

        rag_context = ""
        rag_sources: list[dict[str, Any]] = []

        if use_rag:
            try:
                context = self.rag.get_context_for_prompt(query, top_k=3)
                if context:
                    rag_context = (
                        "\n--- Relevant Documentation ---\n"
                        f"{context}\n"
                        "--- End Documentation ---\n"
                    )

                    results = self.rag.retrieve(query, top_k=3)
                    rag_sources = [
                        {
                            "filename": r.get("metadata", {}).get(
                                "filename", "Unknown"
                            ),
                            "similarity": r.get("similarity", 0),
                        }
                        for r in results
                    ]
            except Exception as exc:
                print(f"RAG retrieval error: {exc}")

        prompt = BUG_ANALYSIS_USER_PROMPT.format(
            title=title,
            description=description,
            environment=environment or "Not specified",
            rag_context=rag_context,
        )

        custom_context = custom_examples_service.get_examples_prompt()
        if custom_context:
            prompt = f"{prompt}\n{custom_context}"

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
                "rag_sources": rag_sources,
                "rag_used": bool(rag_context),
            }

        return {
            "success": False,
            "error": result.get("error"),
            "raw_response": result.get("raw"),
            "latency_ms": result["latency_ms"],
            "model_version": result["model"],
            "prompt_version": self.prompt_version,
            "schema_valid": False,
            "rag_sources": [],
            "rag_used": False,
        }


bug_analyzer = BugAnalyzer()

