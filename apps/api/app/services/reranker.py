from typing import Any, Dict, List

_cross_encoder = None


def get_cross_encoder() -> Any:
    """Lazy load the cross-encoder model."""
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder

            _cross_encoder = CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512
            )
        except Exception as e:
            print(f"Failed to load cross-encoder: {e}")
            _cross_encoder = None
    return _cross_encoder


class Reranker:
    """Cross-encoder reranker for more accurate result ranking."""

    def __init__(self) -> None:
        self.enabled = True
        self._model: Any = None

    @property
    def model(self) -> Any:
        """Lazy load model on first use."""
        if self._model is None:
            self._model = get_cross_encoder()
        return self._model

    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using cross-encoder scoring.

        Args:
            query: The search query
            results: List of retrieval results with 'content' field
            top_k: Number of top results to return

        Returns:
            Reranked results with cross-encoder scores
        """
        if not results:
            return []

        if not self.enabled or self.model is None:
            return results[:top_k]

        try:
            pairs = [(query, r.get("content", "")) for r in results]
            scores = self.model.predict(pairs)

            scored_results = []
            for i, result in enumerate(results):
                result_copy = result.copy()
                result_copy["rerank_score"] = float(scores[i])
                result_copy["original_rank"] = i
                scored_results.append(result_copy)

            scored_results.sort(
                key=lambda x: x["rerank_score"], reverse=True
            )
            return scored_results[:top_k]

        except Exception as e:
            print(f"Reranking error: {e}")
            return results[:top_k]

    def check_health(self) -> Dict[str, Any]:
        """Check reranker health status."""
        try:
            if self.model is not None:
                self.model.predict([("test", "test")])
                return {
                    "status": "ready",
                    "model": "ms-marco-MiniLM-L-6-v2",
                }
            return {"status": "not loaded", "model": None}
        except Exception as e:
            return {"status": "error", "error": str(e)}


reranker = Reranker()
