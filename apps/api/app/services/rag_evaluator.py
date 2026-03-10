import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class RetrievalMetrics:
    """Metrics for a single retrieval operation."""

    query: str
    num_results: int
    latency_ms: float
    avg_similarity: float
    top_similarity: float
    used_hybrid: bool
    used_reranking: bool
    used_expansion: bool
    expansion_variants: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RAGStats:
    """Aggregate RAG statistics."""

    total_queries: int = 0
    avg_latency_ms: float = 0
    avg_results_per_query: float = 0
    avg_top_similarity: float = 0
    hybrid_usage_rate: float = 0
    reranking_usage_rate: float = 0
    expansion_usage_rate: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RAGEvaluator:
    """Track and evaluate RAG performance metrics."""

    def __init__(self, log_file: str = "./data/rag_metrics.jsonl") -> None:
        self.log_file = log_file
        self.metrics_buffer: List[RetrievalMetrics] = []
        self.buffer_size = 100

        dirname = os.path.dirname(log_file)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

    def log_retrieval(
        self,
        query: str,
        results: List[Dict[str, Any]],
        latency_ms: float,
        used_hybrid: bool = True,
        used_reranking: bool = False,
        used_expansion: bool = False,
        expansion_variants: int = 0,
    ) -> RetrievalMetrics:
        """Log a retrieval operation."""
        similarities = [
            r.get("similarity", r.get("combined_score", 0))
            for r in results
        ]

        metrics = RetrievalMetrics(
            query=query[:200],
            num_results=len(results),
            latency_ms=latency_ms,
            avg_similarity=(
                sum(similarities) / len(similarities) if similarities else 0
            ),
            top_similarity=max(similarities) if similarities else 0,
            used_hybrid=used_hybrid,
            used_reranking=used_reranking,
            used_expansion=used_expansion,
            expansion_variants=expansion_variants,
        )

        self.metrics_buffer.append(metrics)

        if len(self.metrics_buffer) >= self.buffer_size:
            self.flush()

        return metrics

    def flush(self) -> None:
        """Write buffered metrics to disk."""
        if not self.metrics_buffer:
            return

        try:
            with open(self.log_file, "a") as f:
                for m in self.metrics_buffer:
                    f.write(json.dumps(m.to_dict()) + "\n")
            self.metrics_buffer = []
        except Exception as e:
            print(f"Error flushing RAG metrics: {e}")

    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics from buffer and file."""
        metrics = [m.to_dict() for m in self.metrics_buffer[-limit:]]

        if len(metrics) < limit and os.path.exists(self.log_file):
            try:
                with open(self.log_file) as f:
                    lines = f.readlines()
                for line in lines[-(limit - len(metrics)) :]:
                    try:
                        metrics.insert(0, json.loads(line.strip()))
                    except Exception:
                        pass
            except Exception:
                pass

        return metrics[-limit:]

    def get_aggregate_stats(self) -> RAGStats:
        """Calculate aggregate statistics."""
        metrics = self.get_recent_metrics(limit=1000)

        if not metrics:
            return RAGStats()

        total = len(metrics)
        return RAGStats(
            total_queries=total,
            avg_latency_ms=sum(m["latency_ms"] for m in metrics) / total,
            avg_results_per_query=sum(m["num_results"] for m in metrics)
            / total,
            avg_top_similarity=sum(m["top_similarity"] for m in metrics)
            / total,
            hybrid_usage_rate=sum(1 for m in metrics if m["used_hybrid"])
            / total,
            reranking_usage_rate=sum(
                1 for m in metrics if m["used_reranking"]
            )
            / total,
            expansion_usage_rate=sum(
                1 for m in metrics if m["used_expansion"]
            )
            / total,
        )

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics_buffer = []
        if os.path.exists(self.log_file):
            os.remove(self.log_file)


rag_evaluator = RAGEvaluator()
