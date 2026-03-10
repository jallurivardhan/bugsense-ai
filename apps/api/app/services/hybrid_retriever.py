from typing import Any, Dict, List

from app.services.embedding_service import embedding_service
from app.services.keyword_search import keyword_search
from app.services.vector_store import vector_store


class HybridRetriever:
    """Hybrid retrieval combining BM25 keyword search and semantic vector search."""

    def __init__(
        self,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
    ) -> None:
        """
        Initialize hybrid retriever.

        Args:
            keyword_weight: Weight for BM25 scores (0-1)
            semantic_weight: Weight for semantic similarity (0-1)
        """
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.keyword_search = keyword_search

    def refresh_keyword_index(self) -> int:
        """Refresh BM25 index from vector store."""
        try:
            all_docs = self.vector_store.collection.get(
                include=["documents", "metadatas"],
            )
            ids = all_docs.get("ids") or []
            if ids:
                documents = all_docs.get("documents") or []
                metadatas = all_docs.get("metadatas") or []
                self.keyword_search.index_documents(
                    doc_ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
                return len(ids)
            return 0
        except Exception as e:
            print(f"Error refreshing keyword index: {e}")
            return 0

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining keyword and semantic results.

        Args:
            query: Search query
            top_k: Number of results to return
            min_score: Minimum combined score threshold

        Returns:
            List of results with combined scores
        """
        if not self.keyword_search.documents:
            self.refresh_keyword_index()

        query_embedding = self.embedding_service.embed_text(query)
        semantic_results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=top_k * 2,
        )

        keyword_results = self.keyword_search.search(
            query, top_k=top_k * 2
        )

        combined_scores: Dict[str, Dict[str, Any]] = {}
        rrf_k = 60

        for rank, result in enumerate(semantic_results):
            meta = result.get("metadata") or {}
            doc_id = f"{meta.get('document_id', '')}_chunk_{meta.get('chunk_index', 0)}"
            rrf_score = 1 / (rrf_k + rank)
            semantic_score = result.get("similarity", 0)

            if doc_id not in combined_scores:
                combined_scores[doc_id] = {
                    "content": result.get("content", ""),
                    "metadata": meta,
                    "semantic_score": semantic_score,
                    "semantic_rrf": rrf_score,
                    "keyword_score": 0.0,
                    "keyword_rrf": 0.0,
                }
            else:
                combined_scores[doc_id]["semantic_score"] = semantic_score
                combined_scores[doc_id]["semantic_rrf"] = rrf_score

        for rank, result in enumerate(keyword_results):
            doc_id = result.get("id", "")
            rrf_score = 1 / (rrf_k + rank)

            if doc_id not in combined_scores:
                combined_scores[doc_id] = {
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "semantic_score": 0.0,
                    "semantic_rrf": 0.0,
                    "keyword_score": result.get("bm25_score", 0),
                    "keyword_rrf": rrf_score,
                }
            else:
                combined_scores[doc_id]["keyword_score"] = result.get(
                    "bm25_score", 0
                )
                combined_scores[doc_id]["keyword_rrf"] = rrf_score

        results: List[Dict[str, Any]] = []
        for doc_id, data in combined_scores.items():
            combined_rrf = (
                self.semantic_weight * data["semantic_rrf"]
                + self.keyword_weight * data["keyword_rrf"]
            )
            normalized_bm25 = min(data["keyword_score"] / 10.0, 1.0)
            combined_score = (
                self.semantic_weight * data["semantic_score"]
                + self.keyword_weight * normalized_bm25
            )

            if combined_score >= min_score or combined_rrf > 0:
                results.append(
                    {
                        "content": data["content"],
                        "metadata": data["metadata"],
                        "semantic_score": data["semantic_score"],
                        "keyword_score": data["keyword_score"],
                        "combined_score": combined_score,
                        "rrf_score": combined_rrf,
                        "similarity": combined_score,
                    }
                )

        results.sort(key=lambda x: x["rrf_score"], reverse=True)
        return results[:top_k]


hybrid_retriever = HybridRetriever()
