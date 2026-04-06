import os
from typing import List

from app.config import settings


class EmbeddingService:
    """Generate embeddings using OpenAI or Ollama."""

    def __init__(self) -> None:
        self.provider = "openai"  # Default to OpenAI
        self.model = "text-embedding-3-small"
        self.client = None
        self.ollama_client = None
        
        # Try OpenAI first
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.provider = "openai"
                print(f"Embedding service using OpenAI: {self.model}")
            except Exception as e:
                print(f"OpenAI embedding init failed: {e}")
        
        # Fallback to Ollama
        if not self.client:
            try:
                import ollama
                self.ollama_client = ollama.Client(host=settings.OLLAMA_BASE_URL)
                self.provider = "ollama"
                self.model = "nomic-embed-text"
                print(f"Embedding service using Ollama: {self.model}")
            except Exception as e:
                print(f"Ollama embedding init failed: {e}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if self.provider == "openai" and self.client:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        elif self.provider == "ollama" and self.ollama_client:
            response = self.ollama_client.embeddings(
                model=self.model,
                prompt=text,
            )
            return response["embedding"]
        else:
            raise RuntimeError("No embedding provider available")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if self.provider == "openai" and self.client:
            # OpenAI supports batch embedding
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        else:
            # Fallback to one-by-one
            return [self.embed_text(text) for text in texts]

    def check_health(self) -> bool:
        """Check if embedding model is available."""
        try:
            self.embed_text("test")
            return True
        except Exception:
            return False


embedding_service = EmbeddingService()
