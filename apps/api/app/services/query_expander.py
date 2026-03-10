from typing import List

from app.services.ai_service import ai_service


class QueryExpander:
    """Expand queries into multiple variants for better retrieval."""

    def __init__(self) -> None:
        self.ai = ai_service

    def expand(self, query: str, num_variants: int = 3) -> List[str]:
        """
        Generate query variants for better retrieval coverage.

        Args:
            query: Original query
            num_variants: Number of variants to generate

        Returns:
            List of query variants including the original
        """
        prompt = f"""Generate {num_variants} different ways to search for information about this query.
Each variant should capture different aspects or use different keywords.

Original query: {query}

Respond with JSON in this exact format:
{{
    "variants": [
        "variant 1",
        "variant 2",
        "variant 3"
    ]
}}

Rules:
- Keep variants concise (under 20 words each)
- Use different keywords and phrasings
- Cover different aspects of the query
- Include technical terms and synonyms

Respond ONLY with JSON, no additional text."""

        result = self.ai.generate(prompt)

        variants = [query]

        if result.get("success"):
            data = result.get("data", {})
            generated = data.get("variants", [])
            for v in generated[:num_variants]:
                if v and v != query:
                    variants.append(v)

        return variants

    def expand_simple(self, query: str) -> List[str]:
        """
        Simple rule-based expansion without LLM.
        Faster but less intelligent.
        """
        variants = [query]

        if query != query.lower():
            variants.append(query.lower())

        synonyms = {
            "bug": ["issue", "defect", "error", "problem"],
            "error": ["bug", "exception", "failure", "fault"],
            "crash": ["failure", "freeze", "hang", "stop working"],
            "slow": ["performance", "latency", "lag", "delay"],
            "cart": ["basket", "shopping cart", "checkout"],
            "login": ["authentication", "sign in", "log in"],
            "user": ["customer", "client", "account"],
        }

        query_lower = query.lower()
        for word, syns in synonyms.items():
            if word in query_lower:
                for syn in syns[:2]:
                    variant = query_lower.replace(word, syn)
                    if variant not in variants:
                        variants.append(variant)

        return variants[:5]


query_expander = QueryExpander()
