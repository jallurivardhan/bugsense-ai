import re
from typing import Any, Dict, List

from rank_bm25 import BM25Okapi


class KeywordSearch:
    """BM25 keyword search for document chunks."""

    def __init__(self) -> None:
        self.documents: List[str] = []
        self.doc_ids: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.bm25: BM25Okapi | None = None

    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase, split on non-alphanumeric."""
        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)
        return tokens

    def index_documents(
        self,
        doc_ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]] | None = None,
    ) -> None:
        """Index documents for BM25 search."""
        self.documents = documents
        self.doc_ids = doc_ids
        self.metadatas = metadatas or [{} for _ in documents]

        tokenized_docs = [self.tokenize(doc) for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for documents matching the query."""
        if not self.bm25 or not self.documents:
            return []

        query_tokens = self.tokenize(query)
        scores = self.bm25.get_scores(query_tokens)

        top_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]

        results: List[Dict[str, Any]] = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(
                    {
                        "id": self.doc_ids[idx],
                        "content": self.documents[idx],
                        "metadata": self.metadatas[idx],
                        "bm25_score": float(scores[idx]),
                    }
                )

        return results

    def clear(self) -> None:
        """Clear the index."""
        self.documents = []
        self.doc_ids = []
        self.metadatas = []
        self.bm25 = None


keyword_search = KeywordSearch()
