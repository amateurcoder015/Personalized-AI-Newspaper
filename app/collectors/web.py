import logging
from typing import List, Optional
from app.database.models import Article

logger = logging.getLogger(__name__)


class WebCollector:
    """Optional web search collector for filling gaps or context when needed."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def search_company_news(self, company_name: str) -> List[Article]:
        """Search news for a specific watchlist company if enabled."""
        if not self.enabled:
            return []
        logger.info(f"Web search for company: {company_name} (Search disabled by default)")
        return []
