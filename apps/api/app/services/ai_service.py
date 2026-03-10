import json
import time
from typing import Any, Dict, Optional

import ollama

from app.config import settings


class AIService:
    def __init__(self, model: str = "llama3.2") -> None:
        self.model = model
        self.client = ollama.Client(host=settings.OLLAMA_BASE_URL)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a response from the AI model."""
        start_time = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                format="json",
            )

            latency_ms = int((time.time() - start_time) * 1000)
            content = response["message"]["content"]

            try:
                parsed = json.loads(content)
                return {
                    "success": True,
                    "data": parsed,
                    "raw": content,
                    "latency_ms": latency_ms,
                    "model": self.model,
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse JSON response",
                    "raw": content,
                    "latency_ms": latency_ms,
                    "model": self.model,
                }

        except Exception as exc:  # pragma: no cover - defensive
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": str(exc),
                "raw": None,
                "latency_ms": latency_ms,
                "model": self.model,
            }

    def check_health(self) -> bool:
        """Check if Ollama is available."""
        try:
            self.client.list()
            return True
        except Exception:
            return False


# Singleton instance
ai_service = AIService()

