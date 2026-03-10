import time
from typing import Any, Dict, List

from app.services.document_processor import document_processor
from app.services.embedding_service import embedding_service
from app.services.hybrid_retriever import hybrid_retriever
from app.services.query_expander import query_expander
from app.services.rag_evaluator import rag_evaluator
from app.services.reranker import reranker
from app.services.text_chunker import text_chunker
from app.services.vector_store import vector_store


class RAGService:
    """Production RAG service with hybrid search, reranking, and query expansion."""

    def __init__(self) -> None:
        self.document_processor = document_processor
        self.text_chunker = text_chunker
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.hybrid_retriever = hybrid_retriever
        self.query_expander = query_expander
        self.reranker = reranker
        self.evaluator = rag_evaluator

        self.use_hybrid = True
        self.use_reranking = True
        self.use_expansion = False

    def index_document(
        self,
        document_id: str,
        file_path: str,
        filename: str,
    ) -> Dict[str, Any]:
        """Process and index a document for RAG."""
        try:
            text = self.document_processor.extract_text(file_path)
            if not text:
                return {
                    "success": False,
                    "error": "No text extracted",
                    "chunks": 0,
                }

            chunks = self.text_chunker.chunk_text(text)
            if not chunks:
                return {
                    "success": False,
                    "error": "No chunks created",
                    "chunks": 0,
                }

            chunk_texts = [c.content for c in chunks]
            embeddings = self.embedding_service.embed_texts(chunk_texts)

            metadatas: List[Dict[str, Any]] = [
                {
                    "filename": filename,
                    "chunk_index": c.index,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                }
                for c in chunks
            ]

            num_chunks = self.vector_store.add_chunks(
                document_id=document_id,
                chunks=chunk_texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            self.hybrid_retriever.refresh_keyword_index()

            return {
                "success": True,
                "chunks": num_chunks,
                "text_length": len(text),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "chunks": 0}

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.3,
        use_expansion: bool | None = None,
        use_reranking: bool | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks using production RAG pipeline.

        Pipeline:
        1. Query Expansion (optional) - Generate query variants
        2. Hybrid Search - BM25 + Semantic
        3. Reranking (optional) - Cross-encoder scoring
        4. Evaluation - Log metrics
        """
        start_time = time.time()

        _use_expansion = (
            use_expansion if use_expansion is not None else self.use_expansion
        )
        _use_reranking = (
            use_reranking
            if use_reranking is not None
            else self.use_reranking
        )

        try:
            queries = [query]
            if _use_expansion:
                queries = self.query_expander.expand_simple(query)

            all_results: List[Dict[str, Any]] = []
            seen_contents: set[str] = set()

            for q in queries:
                if self.use_hybrid:
                    results = self.hybrid_retriever.search(
                        query=q,
                        top_k=top_k * 2,
                        min_score=min_similarity,
                    )
                else:
                    query_embedding = self.embedding_service.embed_text(q)
                    results = self.vector_store.search(
                        query_embedding=query_embedding,
                        n_results=top_k * 2,
                    )

                for r in results:
                    content = r.get("content", "")
                    if content not in seen_contents:
                        seen_contents.add(content)
                        all_results.append(r)

            if _use_reranking and all_results:
                all_results = self.reranker.rerank(
                    query=query,
                    results=all_results,
                    top_k=top_k,
                )
            else:
                all_results = all_results[:top_k]

            latency_ms = (time.time() - start_time) * 1000
            self.evaluator.log_retrieval(
                query=query,
                results=all_results,
                latency_ms=latency_ms,
                used_hybrid=self.use_hybrid,
                used_reranking=_use_reranking,
                used_expansion=_use_expansion,
                expansion_variants=len(queries),
            )

            return all_results

        except Exception as e:
            print(f"RAG retrieval error: {e}")
            return []

    def get_context_for_prompt(
        self,
        query: str,
        top_k: int = 3,
    ) -> str:
        """Get formatted context string for AI prompts."""
        results = self.retrieve(
            query, top_k=top_k, use_reranking=True
        )

        if not results:
            return ""

        context_parts: List[str] = []
        for i, result in enumerate(results, 1):
            filename = (
                result.get("metadata", {}).get("filename", "Unknown")
            )
            content = result.get("content", "")
            score = result.get(
                "rerank_score",
                result.get(
                    "similarity",
                    result.get("combined_score", 0),
                ),
            )
            if "rerank_score" in result:
                score_display = f"{min(max(score, 0), 1) * 100:.0f}%"
                method = "reranked"
            else:
                score_display = f"{score:.0%}"
                method = (
                    "hybrid"
                    if result.get("keyword_score", 0) > 0
                    else "semantic"
                )
            context_parts.append(
                f"[Document {i}: {filename} (relevance: {score_display}, method: {method})]\n{content}"
            )

        return "\n\n---\n\n".join(context_parts)

    def delete_document(self, document_id: str) -> int:
        """Remove a document from the index."""
        count = self.vector_store.delete_document(document_id)
        self.hybrid_retriever.refresh_keyword_index()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive RAG system statistics."""
        vector_stats = self.vector_store.get_stats()
        eval_stats = self.evaluator.get_aggregate_stats()
        reranker_health = self.reranker.check_health()

        return {
            "total_chunks": vector_stats.get("total_chunks", 0),
            "collection_name": vector_stats.get(
                "collection_name", "documents"
            ),
            "search_method": (
                "hybrid" if self.use_hybrid else "semantic"
            ),
            "keyword_indexed": len(
                self.hybrid_retriever.keyword_search.documents
            ),
            "reranker_status": reranker_health.get("status", "unknown"),
            "features": {
                "hybrid_search": self.use_hybrid,
                "reranking": self.use_reranking,
                "query_expansion": self.use_expansion,
            },
            "performance": {
                "total_queries": eval_stats.total_queries,
                "avg_latency_ms": round(eval_stats.avg_latency_ms, 2),
                "avg_results_per_query": round(
                    eval_stats.avg_results_per_query, 2
                ),
                "avg_top_similarity": round(
                    eval_stats.avg_top_similarity, 3
                ),
            },
        }

    def configure(
        self,
        use_hybrid: bool | None = None,
        use_reranking: bool | None = None,
        use_expansion: bool | None = None,
    ) -> None:
        """Configure RAG features at runtime."""
        if use_hybrid is not None:
            self.use_hybrid = use_hybrid
        if use_reranking is not None:
            self.use_reranking = use_reranking
        if use_expansion is not None:
            self.use_expansion = use_expansion


rag_service = RAGService()
