from app.config import UserConfig, RankingConfig
from app.database.models import Article, Story
from app.processing.ranker import StoryRanker


def test_watchlist_ranking_priority():
    user_cfg = UserConfig(
        interests=["Indian stock market", "AI"],
        companies=["Reliance", "NVIDIA"]
    )
    ranking_cfg = RankingConfig()
    ranker = StoryRanker(user_config=user_cfg, ranking_config=ranking_cfg)

    s1 = Story(
        headline="Reliance Industries Announces New $10B AI Data Center in India",
        summary="Reliance and NVIDIA partner to build massive AI infrastructure.",
        sources=["Economic Times"],
        articles=[Article(title="Reliance AI Data Center", url="https://example.com/ril", source="ET")]
    )

    s2 = Story(
        headline="Local Bakery Wins Regional Bread Award",
        summary="A small bakery in a town received a neighborhood prize.",
        sources=["Local Gazette"],
        articles=[Article(title="Local Bakery Award", url="https://example.com/bakery", source="LG")]
    )

    ranked = ranker.rank_stories([s2, s1])
    assert len(ranked) == 2
    assert ranked[0].headline == s1.headline
    assert ranked[0].final_score > ranked[1].final_score
    assert "Reliance" in ranked[0].matched_watchlist or "Nvidia" in ranked[0].matched_watchlist
