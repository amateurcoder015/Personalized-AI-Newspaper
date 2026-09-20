import logging
from typing import List, Set
from app.config import UserConfig, RankingConfig
from app.database.models import Story

logger = logging.getLogger(__name__)

MAJOR_EVENT_KEYWORDS = {
    "rbi", "repo rate", "fed", "federal reserve", "gdp", "inflation",
    "interest rates", "fiscal", "central bank", "earnings", "acquisition",
    "merger", "ipo", "funding", "ai", "llm", "revenue", "policy"
}

MARKET_IMPACT_KEYWORDS = {
    "nifty", "sensex", "nasdaq", "bonds", "yield", "currency", "dollar",
    "rupee", "oil", "crude", "stock", "shares", "rally", "plunge", "surge"
}


class StoryRanker:
    """Ranks stories based on Global Importance and Personal Relevance."""

    def __init__(self, user_config: UserConfig, ranking_config: RankingConfig):
        self.user_config = user_config
        self.ranking_config = ranking_config
        self.watchlist: Set[str] = {c.lower() for c in user_config.companies}
        self.interests: Set[str] = {i.lower() for i in user_config.interests}

    def compute_importance(self, story: Story) -> float:
        score = 0.0
        headline_lower = story.headline.lower()
        summary_lower = story.summary.lower()
        full_text = f"{headline_lower} {summary_lower}"

        # Major event match
        if any(kw in full_text for kw in MAJOR_EVENT_KEYWORDS):
            score += self.ranking_config.major_event_weight

        # Multiple reputable sources covering same event
        if len(story.sources) > 1:
            score += self.ranking_config.multiple_sources_weight

        # Recency (default +2.0 for fresh pipeline run)
        score += self.ranking_config.recency_weight

        # Market impact
        if any(kw in full_text for kw in MARKET_IMPACT_KEYWORDS):
            score += self.ranking_config.market_impact_weight

        # Topic match
        if any(interest in full_text for interest in self.interests):
            score += self.ranking_config.topic_match_weight

        return round(score, 2)

    def compute_relevance(self, story: Story) -> (float, List[str]):
        score = 0.0
        matched_watchlist = []
        headline_lower = story.headline.lower()
        summary_lower = story.summary.lower()
        full_text = f"{headline_lower} {summary_lower}"

        # Watchlist match (+3 per match or config weight)
        for company in self.watchlist:
            if company in full_text:
                score += self.ranking_config.watchlist_match_weight
                matched_watchlist.append(company.title())

        # Interest match
        for interest in self.interests:
            if interest in full_text:
                score += 1.5

        return round(score, 2), matched_watchlist

    def rank_stories(self, stories: List[Story]) -> List[Story]:
        for story in stories:
            imp = self.compute_importance(story)
            rel, matched = self.compute_relevance(story)

            story.importance_score = imp
            story.relevance_score = rel
            story.matched_watchlist = matched

            # Calculate weighted final score
            story.final_score = round(
                (self.ranking_config.global_importance_weight * imp) +
                (self.ranking_config.personal_relevance_weight * rel),
                2
            )

        # Sort descending by final score
        ranked = sorted(stories, key=lambda s: s.final_score, reverse=True)
        logger.info(f"Ranking: Ranked {len(ranked)} stories. Top story score: {ranked[0].final_score if ranked else 0}")
        return ranked
