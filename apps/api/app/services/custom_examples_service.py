from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CustomExample


class CustomExamplesService:
    def __init__(self) -> None:
        self.examples_cache: List[Dict[str, Any]] = []

    async def load_from_db(self, db: AsyncSession) -> None:
        """Load custom examples from database."""
        try:
            result = await db.execute(
                select(CustomExample).where(CustomExample.is_active.is_(True))
            )
            examples = result.scalars().all()
            self.examples_cache = [
                {
                    "id": str(ex.id),
                    "title": ex.title,
                    "description": ex.description,
                    "severity": ex.severity,
                    "priority": ex.priority,
                    "reasoning": ex.reasoning,
                    "domain": ex.domain,
                }
                for ex in examples
            ]
            print(f"Loaded {len(self.examples_cache)} custom examples from database")
        except Exception as e:
            print(f"Error loading custom examples: {e}")
            self.examples_cache = []

    async def add_example(self, db: AsyncSession, example: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new custom example."""
        domain = example.get("domain")
        if domain == "":
            domain = None
        new_example = CustomExample(
            title=example["title"],
            description=example.get("description") or None,
            severity=example["severity"],
            priority=example["priority"],
            reasoning=example.get("reasoning") or None,
            domain=domain or "general",
        )
        db.add(new_example)
        await db.commit()
        await db.refresh(new_example)

        entry = {
            "id": str(new_example.id),
            "title": new_example.title,
            "description": new_example.description,
            "severity": new_example.severity,
            "priority": new_example.priority,
            "reasoning": new_example.reasoning,
            "domain": new_example.domain,
        }
        self.examples_cache.append(entry)

        return {"success": True, "id": str(new_example.id)}

    async def delete_example(self, db: AsyncSession, example_id: str) -> Dict[str, Any]:
        """Delete a custom example."""
        try:
            ex_uuid = UUID(example_id)
        except ValueError:
            return {"success": False, "error": "Invalid example id"}

        result = await db.execute(select(CustomExample).where(CustomExample.id == ex_uuid))
        example = result.scalar_one_or_none()
        if not example:
            return {"success": False, "error": "Example not found"}

        await db.execute(delete(CustomExample).where(CustomExample.id == ex_uuid))
        await db.commit()
        self.examples_cache = [ex for ex in self.examples_cache if ex["id"] != example_id]
        return {"success": True}

    def get_examples(self) -> List[Dict[str, Any]]:
        """Get all custom examples."""
        return self.examples_cache

    def get_examples_prompt(self) -> str:
        """Generate few-shot prompt from custom examples."""
        if not self.examples_cache:
            return ""

        by_severity: Dict[str, List[Dict[str, Any]]] = {
            "Critical": [],
            "High": [],
            "Medium": [],
            "Low": [],
        }
        for ex in self.examples_cache:
            sev = ex["severity"]
            if sev in by_severity and len(by_severity[sev]) < 5:
                by_severity[sev].append(ex)

        prompt = "\n=== CUSTOM EXAMPLES FROM YOUR DOMAIN ===\n"

        for severity in ["Critical", "High", "Medium", "Low"]:
            examples = by_severity[severity]
            if examples:
                prompt += f"\n**{severity.upper()} Examples:**\n"
                for ex in examples:
                    prompt += f"• \"{ex['title']}\" → {severity} {ex['priority']}"
                    if ex.get("reasoning"):
                        prompt += f" ({ex['reasoning']})"
                    prompt += "\n"

        prompt += "\nUse these examples to guide your classification.\n"
        return prompt


custom_examples_service = CustomExamplesService()
