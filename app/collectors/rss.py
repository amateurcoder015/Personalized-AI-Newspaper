import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import feedparser
import requests
from bs4 import BeautifulSoup
from app.database.models import Article

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class RSSCollector:
    """Collects RSS news feeds with explicit timeouts, retries, error logging, and source health tracking."""

    def __init__(
        self,
        sources: Dict[str, List[Any]],
        max_per_source: int = 20,
        request_timeout: int = 10,
        max_retries: int = 3
    ):
        self.sources = sources
        self.max_per_source = max_per_source
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.source_health: Dict[str, str] = {}

    def fetch_feed_content(self, url: str, source_name: str) -> Optional[str]:
        """Fetch raw XML feed content with retries and exponential backoff."""
        headers = {"User-Agent": USER_AGENT}
        
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(url, headers=headers, timeout=self.request_timeout)
                if response.status_code == 200:
                    self.source_health[source_name] = "✓ OK"
                    return response.text
                else:
                    logger.warning(f"Attempt {attempt}/{self.max_retries} - RSS feed '{source_name}' ({url}) returned HTTP status {response.status_code}")
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} - Error requesting RSS feed '{source_name}' ({url}): {e}")
            
            if attempt < self.max_retries:
                time.sleep(attempt * 1.5)

        logger.warning(f"WARNING: '{source_name}' RSS feed unavailable after {self.max_retries} retries. Continuing with remaining sources...")
        self.source_health[source_name] = "⚠ WARNING (Unavailable)"
        return None

    def parse_entry(self, entry: Dict[str, Any], source_name: str, category: str) -> Optional[Article]:
        """Parse individual RSS feed entry into standardized Article object."""
        try:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()

            if not title or not url:
                return None

            description_raw = entry.get("summary", "") or entry.get("description", "")
            description = BeautifulSoup(description_raw, "html.parser").get_text().strip() if description_raw else ""

            content = ""
            if "content" in entry and len(entry["content"]) > 0:
                content_raw = entry["content"][0].get("value", "")
                content = BeautifulSoup(content_raw, "html.parser").get_text().strip()
            if not content:
                content = description

            published_at = entry.get("published", "") or entry.get("updated", "")
            if not published_at:
                published_at = datetime.now(timezone.utc).isoformat()

            author = entry.get("author", "") or source_name

            image_url = None
            if "media_content" in entry and len(entry["media_content"]) > 0:
                image_url = entry["media_content"][0].get("url")
            elif "enclosures" in entry and len(entry["enclosures"]) > 0:
                image_url = entry["enclosures"][0].get("href")

            topics = []
            if "tags" in entry:
                topics = [tag.get("term", "") for tag in entry["tags"] if tag.get("term")]

            # Detect primary source preference (official announcements, SEC filings, RBI releases)
            is_primary = False
            title_lower = title.lower()
            if any(term in title_lower for term in ["rbi announcement", "sec filing", "official release", "press release", "bse filing", "nse filing"]):
                is_primary = True

            return Article(
                title=title,
                description=description[:500],
                content=content[:2000],
                url=url,
                source=source_name,
                author=author,
                published_at=published_at,
                category=category,
                image_url=image_url,
                topics=topics,
                is_primary_source=is_primary
            )
        except Exception as e:
            logger.debug(f"Failed to parse entry from {source_name}: {e}")
            return None

    def collect(self) -> List[Article]:
        """Collect articles from all configured RSS feeds with timeout and retry controls."""
        all_articles: List[Article] = []

        for category, source_list in self.sources.items():
            for src in source_list:
                if isinstance(src, dict):
                    source_name = src.get("name", "Unknown Source")
                    source_url = src.get("url", "")
                else:
                    source_name = getattr(src, "name", "Unknown Source")
                    source_url = getattr(src, "url", "")

                if not source_url:
                    continue

                logger.info(f"Fetching RSS feed: {source_name} ({source_url})")
                feed_xml = self.fetch_feed_content(source_url, source_name)

                if not feed_xml:
                    continue

                try:
                    feed = feedparser.parse(feed_xml)
                    parsed_count = 0
                    for entry in feed.entries[:self.max_per_source]:
                        article = self.parse_entry(entry, source_name, category)
                        if article:
                            all_articles.append(article)
                            parsed_count += 1
                    logger.info(f"Retrieved {parsed_count} articles from '{source_name}'")
                except Exception as e:
                    logger.warning(f"Error parsing RSS XML feed for '{source_name}': {e}")
                    self.source_health[source_name] = "⚠ WARNING (Parse Error)"

        logger.info(f"RSS Collection Complete: Total {len(all_articles)} raw articles collected across {len(self.source_health)} feeds.")
        return all_articles
