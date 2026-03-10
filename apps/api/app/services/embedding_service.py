import ollama
from typing import List

from app.config import settings


class EmbeddingService:
    """Generate embeddings using Ollama."""

    def __init__(self, model: str = "nomic-embed-text") -> None:
        self.model = model
        self.client = ollama.Client(host=settings.OLLAMA_BASE_URL)

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        response = self.client.embeddings(
            model=self.model,
            prompt=text,
        )
        return response["embedding"]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings: List[List[float]] = []
        for text in texts:
            embedding = self.embed_text(text)
            embeddings.append(embedding)
        return embeddings

    def check_health(self) -> bool:
        """Check if embedding model is available."""
        try:
            self.embed_text("test")
            return True
        except Exception:
            return False


embedding_service = EmbeddingService()

