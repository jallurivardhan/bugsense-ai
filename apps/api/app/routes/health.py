from fastapi import APIRouter

from app.services.ai_service import ai_service

router = APIRouter()


@router.get("")
async def health_check():
    """Check API and Ollama health."""
    ollama_healthy = ai_service.check_health()

    return {
        "status": "healthy",
        "ollama": {
            "status": "connected" if ollama_healthy else "disconnected",
            "model": ai_service.model,
        },
    }
