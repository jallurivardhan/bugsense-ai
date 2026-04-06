"""
Hybrid AI Service — OpenAI, Groq (cloud), and Ollama (local).
"""

import json
import re
import time
from typing import Any, Dict, Optional

import httpx

from app.config import settings


class AIService:
    """Hybrid AI service supporting multiple providers."""

    def __init__(self) -> None:
        self.provider = self._determine_provider()
        self.groq_client: Any = None
        self.openai_client: Any = None

        if self.provider == "groq":
            self._init_groq()
        elif self.provider == "openai":
            self._init_openai()

        print(f"AI Service initialized with provider: {self.provider}")

    def _determine_provider(self) -> str:
        """Determine which AI provider to use based on available keys."""
        if settings.AI_PROVIDER == "openai":
            return "openai"
        if settings.AI_PROVIDER == "groq":
            return "groq"
        if settings.AI_PROVIDER == "ollama":
            return "ollama"
        # auto — prefer OpenAI > Groq > Ollama
        if settings.OPENAI_API_KEY:
            return "openai"
        if settings.GROQ_API_KEY:
            return "groq"
        return "ollama"

    def _init_groq(self) -> None:
        """Initialize Groq client."""
        try:
            from groq import Groq

            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
            print(f"Groq client initialized with model: {settings.GROQ_MODEL}")
        except ImportError:
            print("Groq package not installed. Falling back to Ollama.")
            self.provider = "ollama"
            self.groq_client = None
        except Exception as e:
            print(f"Failed to initialize Groq: {e}. Falling back to Ollama.")
            self.provider = "ollama"
            self.groq_client = None

    def _init_openai(self) -> None:
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI

            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            print(f"OpenAI client initialized with model: {settings.OPENAI_MODEL}")
        except ImportError:
            print("OpenAI package not installed. Install with: pip install openai")
            self.provider = "ollama"
            self.openai_client = None
        except Exception as e:
            print(f"Failed to initialize OpenAI: {e}")
            self.provider = "ollama"
            self.openai_client = None

    @property
    def model(self) -> str:
        """Active model name (for metrics / health)."""
        if self.provider == "openai":
            return settings.OPENAI_MODEL
        if self.provider == "groq":
            return settings.GROQ_MODEL
        return settings.OLLAMA_MODEL

    def get_provider_info(self) -> Dict[str, Any]:
        """Get current provider information."""
        if self.provider == "openai":
            return {
                "provider": "openai",
                "model": settings.OPENAI_MODEL,
                "speed": "fast",
                "avg_latency_seconds": 2,
                "privacy": "cloud",
                "accuracy": "high",
            }
        if self.provider == "groq":
            return {
                "provider": "groq",
                "model": settings.GROQ_MODEL,
                "speed": "fast",
                "avg_latency_seconds": 2,
                "privacy": "cloud",
                "accuracy": "medium",
            }
        return {
            "provider": "ollama",
            "model": settings.OLLAMA_MODEL,
            "speed": "slow",
            "avg_latency_seconds": 60,
            "privacy": "local",
            "accuracy": "medium",
        }

    def check_health(self) -> bool:
        """Check whether the active AI backend is reachable."""
        if self.provider == "openai":
            return self.openai_client is not None
        if self.provider == "groq":
            return self.groq_client is not None
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                return response.is_success
        except Exception:
            return False

    def switch_provider(self, provider: str) -> bool:
        """Switch to a different AI provider."""
        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                print("Cannot switch to OpenAI: No API key configured")
                return False
            self._init_openai()
            if self.openai_client:
                self.provider = "openai"
                print("Switched to provider: openai")
                return True
            return False

        if provider == "groq":
            if not settings.GROQ_API_KEY:
                print("Cannot switch to Groq: No API key configured")
                return False
            self._init_groq()
            if self.groq_client:
                self.provider = "groq"
                print("Switched to provider: groq")
                return True
            return False

        if provider == "ollama":
            self.provider = "ollama"
            print("Switched to provider: ollama")
            return True

        return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Generate a response using the configured provider.

        Returns shape expected by bug_analyzer, test_generator, etc.:
        success, data, raw, latency_ms, model, and optional error.
        """
        start_time = time.time()
        model_name = self.model

        if self.provider == "openai" and self.openai_client is not None:
            inner = self._generate_openai(prompt, system_prompt, format)
        elif self.provider == "groq" and self.groq_client is not None:
            inner = self._generate_groq(prompt, system_prompt, format)
        else:
            inner = self._generate_ollama(prompt, system_prompt, format)

        latency_ms = int((time.time() - start_time) * 1000)
        out: Dict[str, Any] = {
            "success": inner["success"],
            "data": inner.get("data"),
            "raw": inner.get("content"),
            "latency_ms": latency_ms,
            "model": model_name,
        }
        if inner.get("error"):
            out["error"] = inner["error"]
        return out

    def _strip_json_fences(self, content: str) -> str:
        content = re.sub(r"^```json\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"^```\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        return content.strip()

    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        format: str,
    ) -> Dict[str, Any]:
        """Generate response using OpenAI API."""
        try:
            system_message = (
                system_prompt
                or "You are a helpful AI assistant for software testing and bug analysis."
            )
            if format == "json":
                system_message += (
                    " Always respond with valid JSON only. "
                    "No markdown, no explanation, just JSON."
                )

            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=4096,
            )

            content = response.choices[0].message.content or ""

            if format == "json":
                cleaned = self._strip_json_fences(content)
                try:
                    parsed = json.loads(cleaned)
                    return {
                        "success": True,
                        "content": cleaned,
                        "data": parsed,
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "content": cleaned,
                        "data": None,
                        "error": "Failed to parse JSON response",
                    }

            return {"success": True, "content": content, "data": None}

        except Exception as e:
            print(f"OpenAI generation error: {e}")
            return {
                "success": False,
                "content": None,
                "data": None,
                "error": str(e),
            }

    def _generate_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        format: str,
    ) -> Dict[str, Any]:
        """Generate response using Groq API."""
        try:
            system_message = system_prompt or "You are a helpful AI assistant."
            if format == "json":
                system_message += (
                    " Always respond with valid JSON only. "
                    "No markdown, no explanation, just JSON."
                )

            response = self.groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=4096,
            )

            content = response.choices[0].message.content or ""

            if format == "json":
                cleaned = self._strip_json_fences(content)
                try:
                    parsed = json.loads(cleaned)
                    return {
                        "success": True,
                        "content": cleaned,
                        "data": parsed,
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "content": cleaned,
                        "data": None,
                        "error": "Failed to parse JSON response",
                    }

            return {"success": True, "content": content, "data": None}

        except Exception as e:
            print(f"Groq generation error: {e}")
            return {
                "success": False,
                "content": None,
                "data": None,
                "error": str(e),
            }

    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        format: str,
    ) -> Dict[str, Any]:
        """Generate response using local Ollama HTTP API."""
        try:
            url = f"{settings.OLLAMA_BASE_URL}/api/generate"
            payload: Dict[str, Any] = {
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            }
            if system_prompt:
                payload["system"] = system_prompt
            if format == "json":
                payload["format"] = "json"

            with httpx.Client(timeout=300.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

            content = result.get("response", "")

            if format == "json":
                try:
                    parsed = json.loads(content)
                    return {
                        "success": True,
                        "content": content,
                        "data": parsed,
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "content": content,
                        "data": None,
                        "error": "Failed to parse JSON response",
                    }

            return {"success": True, "content": content, "data": None}

        except Exception as e:
            print(f"Ollama generation error: {e}")
            return {
                "success": False,
                "content": None,
                "data": None,
                "error": str(e),
            }


ai_service = AIService()
