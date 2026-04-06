import json
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

_api_root = Path(__file__).resolve().parent.parent
_env_local = _api_root / ".env.local"
_env_file = _api_root / ".env"

print(f"Looking for .env.local at: {_env_local}")
print(f".env.local exists: {_env_local.exists()}")

if _env_local.exists():
    load_dotenv(_env_local, override=True)
    print(f"Loaded .env.local")

if _env_file.exists():
    load_dotenv(_env_file)
    print(f"Loaded .env")

_groq_key = os.getenv("GROQ_API_KEY")
print(f"GROQ_API_KEY loaded: {'Yes (' + _groq_key[:10] + '...)' if _groq_key else 'No'}")


class Settings(BaseSettings):
    APP_NAME: str = "BugSense AI"
    APP_TAGLINE: str = "AI Assistant for Software Testing"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # CORS - Allow all origins for development
    CORS_ORIGINS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_testing"
    )

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # Groq
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # AI Provider
    AI_PROVIDER: str = "auto"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes")
        return v

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()

print(f"Final GROQ_API_KEY in settings: {'Yes' if settings.GROQ_API_KEY else 'No'}")
print(f"AI_PROVIDER setting: {settings.AI_PROVIDER}")
