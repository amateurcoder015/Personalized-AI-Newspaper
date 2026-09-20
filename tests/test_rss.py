from unittest.mock import patch, MagicMock
from app.collectors.rss import RSSCollector
from app.database.models import Article


def test_parse_entry_valid():
    collector = RSSCollector(sources={})
    entry = {
        "title": "RBI Keeps Policy Rate Unchanged at 6.5%",
        "link": "https://example.com/rbi-rate",
        "summary": "<p>The central bank kept interest rates steady.</p>",
        "published": "2026-09-20T07:00:00Z",
        "author": "Financial Bureau"
    }

    article = collector.parse_entry(entry, source_name="Test Bureau", category="india")
    assert article is not None
    assert article.title == "RBI Keeps Policy Rate Unchanged at 6.5%"
    assert article.url == "https://example.com/rbi-rate"
    assert "kept interest rates steady" in article.description
    assert article.category == "india"


def test_parse_entry_missing_fields():
    collector = RSSCollector(sources={})
    entry = {"summary": "No title or link available"}
    article = collector.parse_entry(entry, source_name="Test Bureau", category="india")
    assert article is None


@patch("app.collectors.rss.RSSCollector.fetch_feed_content")
def test_rss_collect_valid_feed(mock_fetch):
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Sample Feed</title>
            <item>
                <title>TCS Announces Q3 Results</title>
                <link>https://example.com/tcs-q3</link>
                <description>TCS net profit rose 8 percent year-on-year.</description>
            </item>
        </channel>
    </rss>
    """
    mock_fetch.return_value = sample_xml

    collector = RSSCollector(sources={"companies": [{"name": "Sample Feed", "url": "https://example.com/rss"}]})
    articles = collector.collect()

    assert len(articles) == 1
    assert articles[0].title == "TCS Announces Q3 Results"
    assert articles[0].source == "Sample Feed"
