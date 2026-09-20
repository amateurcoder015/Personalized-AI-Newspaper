import re
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from typing import List
from bs4 import BeautifulSoup
from app.database.models import Article


class ArticleCleaner:
    """Cleans article titles, descriptions, content, and normalizes URLs."""

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        # Remove HTML tags
        soup = BeautifulSoup(text, "html.parser")
        cleaned = soup.get_text(separator=" ")
        # Replace multiple whitespaces/newlines with single space
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def normalize_url(url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        # Filter out common tracking query params
        query_params = parse_qs(parsed.query)
        filtered_params = {
            k: v for k, v in query_params.items()
            if not k.startswith("utm_") and k not in ("fbclid", "gclid", "ref")
        }
        new_query = urlencode(filtered_params, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))

    def clean_article(self, article: Article) -> Article:
        article.title = self.clean_text(article.title)
        article.description = self.clean_text(article.description)
        article.content = self.clean_text(article.content)
        article.url = self.normalize_url(article.url)
        return article

    def clean_articles(self, articles: List[Article]) -> List[Article]:
        cleaned = []
        for article in articles:
            c = self.clean_article(article)
            if c.title and c.url:
                cleaned.append(c)
        return cleaned
