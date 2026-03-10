from fastapi import APIRouter

from app.services.ai_service import ai_service
from app.services.rag_service import rag_service

router = APIRouter()


@router.get("")
async def health_check():
    """Check API, Ollama, and RAG health."""
    ollama_healthy = ai_service.check_health()

    try:
        rag_stats = rag_service.get_stats()
    except Exception:
        rag_stats = {"total_chunks": 0}

    return {
        "status": "healthy",
        "ollama": {
            "status": "connected" if ollama_healthy else "disconnected",
            "model": ai_service.model,
        },
        "rag": {
            "status": "active" if rag_stats["total_chunks"] > 0 else "no documents",
            "indexed_chunks": rag_stats["total_chunks"],
        },
    }
