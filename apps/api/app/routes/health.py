from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get("")
async def health_check():
    """Health check endpoint with AI provider info."""
    from app.services.ai_service import ai_service

    provider_info = ai_service.get_provider_info()

    return {
        "status": "healthy",
        "service": "BugSense AI API",
        "ai_provider": provider_info,
    }


@router.post("/switch-provider")
async def switch_provider(provider: str = Query(...)):
    """Switch AI provider (openai, groq, or ollama)."""
    from app.services.ai_service import ai_service

    if provider not in ("openai", "groq", "ollama"):
        raise HTTPException(
            status_code=400,
            detail="Provider must be 'openai', 'groq', or 'ollama'",
        )

    success = ai_service.switch_provider(provider)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to switch to {provider}. Check if it's available.",
        )

    return {
        "message": f"Switched to {provider}",
        "ai_provider": ai_service.get_provider_info(),
    }


@router.get("/available-providers")
async def get_available_providers():
    """Get list of available AI providers."""
    from app.config import settings
    from app.services.ai_service import ai_service

    providers = [
        {
            "id": "ollama",
            "name": "Ollama (Local)",
            "description": "Private, runs locally, ~60s/request",
            "available": True,
            "privacy": "local",
            "speed": "slow",
            "accuracy": "medium",
        },
        {
            "id": "groq",
            "name": "Groq (Free Cloud)",
            "description": "Fast, free tier, ~2s/request",
            "available": bool(settings.GROQ_API_KEY),
            "privacy": "cloud",
            "speed": "fast",
            "accuracy": "medium",
        },
        {
            "id": "openai",
            "name": "OpenAI (GPT-4o)",
            "description": "High accuracy, ~2s/request",
            "available": bool(settings.OPENAI_API_KEY),
            "privacy": "cloud",
            "speed": "fast",
            "accuracy": "high",
        },
    ]

    return {
        "providers": providers,
        "current": ai_service.provider,
    }
