import logging
from typing import Dict, Any, List, Optional
from app.database import DatabaseManager
from app.learning.concepts import FINANCE_CONCEPTS_REPOSITORY

logger = logging.getLogger(__name__)


class ConceptSelector:
    """Selects relevant finance concepts linked to today's news while preventing repetition within 30 days."""

    def __init__(self, db: DatabaseManager, avoid_recent_days: int = 30):
        self.db = db
        self.avoid_recent_days = avoid_recent_days

    def select_concept(self, headlines_text: str) -> Dict[str, Any]:
        recently_used = self.db.get_recent_used_concepts(days=self.avoid_recent_days)
        available = [c for c in FINANCE_CONCEPTS_REPOSITORY if c["concept"] not in recently_used]

        if not available:
            logger.info("All concepts used recently; resetting pool.")
            available = FINANCE_CONCEPTS_REPOSITORY

        text_lower = headlines_text.lower()
        best_match = None
        highest_score = -1

        for item in available:
            score = 0
            for kw in item["keywords"]:
                if kw in text_lower:
                    score += 1
            if score > highest_score:
                highest_score = score
                best_match = item

        chosen = best_match or available[0]
        self.db.record_concept_used(chosen["concept"], related_story=headlines_text[:100])
        logger.info(f"Selected Finance Concept: '{chosen['concept']}' (Avoided {len(recently_used)} recent concepts)")
        return chosen
