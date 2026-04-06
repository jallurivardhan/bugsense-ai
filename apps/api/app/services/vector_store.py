import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings


class VectorStore:
  """ChromaDB vector store for document chunks (local persist or remote HttpClient)."""

  def __init__(self, persist_directory: str = "./data/chroma") -> None:
    chroma_host = (os.getenv("CHROMA_HOST") or "").strip()
    chroma_port = int(os.getenv("CHROMA_PORT") or "8000")
    chroma_settings = ChromaSettings(anonymized_telemetry=False)

    if chroma_host:
      self.client = chromadb.HttpClient(
        host=chroma_host,
        port=chroma_port,
        settings=chroma_settings,
      )
    else:
      Path(persist_directory).mkdir(parents=True, exist_ok=True)
      self.client = chromadb.PersistentClient(
        path=persist_directory,
        settings=chroma_settings,
      )

    # Get or create collection
    self.collection = self.client.get_or_create_collection(
      name="documents",
      metadata={"hnsw:space": "cosine"},
    )

  def add_chunks(
    self,
    document_id: str,
    chunks: List[str],
    embeddings: List[List[float]],
    metadatas: Optional[List[Dict[str, Any]]] = None,
  ) -> int:
    """Add document chunks with embeddings to the store."""
    if not chunks:
      return 0

    # Generate unique IDs for each chunk
    ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]

    # Prepare metadata
    if metadatas is None:
      metadatas = [
        {"document_id": document_id, "chunk_index": i}
        for i in range(len(chunks))
      ]
    else:
      for i, meta in enumerate(metadatas):
        meta["document_id"] = document_id
        meta["chunk_index"] = i

    # Add to collection
    self.collection.add(
      ids=ids,
      embeddings=embeddings,
      documents=chunks,
      metadatas=metadatas,
    )

    return len(chunks)

  def search(
    self,
    query_embedding: List[float],
    n_results: int = 5,
    filter_dict: Optional[Dict[str, Any]] = None,
  ) -> List[Dict[str, Any]]:
    """Search for similar chunks."""
    results = self.collection.query(
      query_embeddings=[query_embedding],
      n_results=n_results,
      where=filter_dict,
      include=["documents", "metadatas", "distances"],
    )

    formatted: List[Dict[str, Any]] = []
    if results.get("documents") and results["documents"][0]:
      docs = results["documents"][0]
      metas = results.get("metadatas", [[]])[0]
      dists = results.get("distances", [[]])[0]
      for i, doc in enumerate(docs):
        distance = dists[i] if dists else 0
        formatted.append(
          {
            "content": doc,
            "metadata": metas[i] if metas else {},
            "distance": distance,
            "similarity": 1 - distance if dists else 1,
          }
        )

    return formatted

  def delete_document(self, document_id: str) -> int:
    """Delete all chunks for a document."""
    results = self.collection.get(
      where={"document_id": document_id},
      include=[],
    )

    if results.get("ids"):
      ids = results["ids"]
      self.collection.delete(ids=ids)
      return len(ids)
    return 0

  def get_stats(self) -> Dict[str, Any]:
    """Get collection statistics."""
    return {
      "total_chunks": self.collection.count(),
      "collection_name": self.collection.name,
    }


vector_store = VectorStore()

