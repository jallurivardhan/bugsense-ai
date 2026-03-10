from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Assistant for Software Testing"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_testing"
    )

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    class Config:
        env_file = ".env"


settings = Settings()
