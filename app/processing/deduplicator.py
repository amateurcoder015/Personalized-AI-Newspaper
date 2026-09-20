import logging
from typing import List, Set
from rapidfuzz import fuzz
from app.database.models import Article

logger = logging.getLogger(__name__)


class ArticleDeduplicator:
    """Deduplicates articles in two stages:
    Level 1: Exact URL match / URL Hash
    Level 2: High headline similarity (e.g. RapidFuzz ratio > 82%)
    """

    def __init__(self, similarity_threshold: float = 82.0):
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, articles: List[Article]) -> List[Article]:
        unique_articles: List[Article] = []
        seen_urls: Set[str] = set()

        for article in articles:
            # Level 1: URL check
            if article.url in seen_urls:
                continue

            # Level 2: Title similarity check against already selected unique articles
            is_similar = False
            for existing in unique_articles:
                ratio = fuzz.token_sort_ratio(article.title.lower(), existing.title.lower())
                if ratio >= self.similarity_threshold:
                    is_similar = True
                    logger.debug(f"Duplicate title ignored (ratio {ratio}%): '{article.title}' vs '{existing.title}'")
                    break

            if not is_similar:
                seen_urls.add(article.url)
                unique_articles.append(article)

        logger.info(f"Deduplication: Reduced {len(articles)} articles to {len(unique_articles)} unique articles")
        return unique_articles
