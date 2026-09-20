from app.database.models import Article
from app.processing.cleaner import ArticleCleaner
from app.processing.deduplicator import ArticleDeduplicator
from app.processing.clustering import StoryClusterer


def test_url_deduplication():
    dedup = ArticleDeduplicator()
    a1 = Article(title="NVIDIA Announces New Chip", url="https://example.com/nvidia?utm_source=rss", source="Tech1")
    a2 = Article(title="NVIDIA Announces New GPU", url="https://example.com/nvidia?utm_source=rss", source="Tech2")

    articles = [a1, a2]
    unique = dedup.deduplicate(articles)
    assert len(unique) == 1


def test_headline_similarity_deduplication():
    dedup = ArticleDeduplicator(similarity_threshold=80.0)
    a1 = Article(title="RBI Keeps Repo Rate Unchanged at 6.5%", url="https://example.com/a1", source="News1")
    a2 = Article(title="RBI Keeps Interest Repo Rate Unchanged at 6.5%", url="https://example.com/a2", source="News2")
    a3 = Article(title="Apple Launches New iPhone 16 Pro", url="https://example.com/a3", source="News3")

    articles = [a1, a2, a3]
    unique = dedup.deduplicate(articles)
    assert len(unique) == 2
    titles = [a.title for a in unique]
    assert "Apple Launches New iPhone 16 Pro" in titles


def test_story_clustering():
    clusterer = StoryClusterer(cluster_threshold=60.0)
    a1 = Article(title="Federal Reserve Cuts Rates by 50 bps", url="https://example.com/fed1", source="Reuters")
    a2 = Article(title="US Fed Cuts Benchmark Rate by 50 Basis Points", url="https://example.com/fed2", source="Bloomberg")
    a3 = Article(title="NVIDIA Stock Surges After Earnings Beat", url="https://example.com/nvda", source="CNBC")

    stories = clusterer.cluster_articles([a1, a2, a3])
    assert len(stories) == 2
    fed_story = [s for s in stories if "Federal Reserve" in s.headline or "Fed" in s.headline][0]
    assert len(fed_story.articles) == 2
    assert "Reuters" in fed_story.sources
    assert "Bloomberg" in fed_story.sources
