import logging
from typing import List
from rapidfuzz import fuzz
from app.database.models import Article, Story

logger = logging.getLogger(__name__)


class StoryClusterer:
    """Level 3 Deduplication & Event Grouping:
    Groups multiple articles covering the same real-world event into a unified Story object.
    """

    def __init__(self, cluster_threshold: float = 62.0):
        self.cluster_threshold = cluster_threshold

    def cluster_articles(self, articles: List[Article]) -> List[Story]:
        clusters: List[List[Article]] = []

        for article in articles:
            matched_cluster = None
            for cluster in clusters:
                # Check similarity against primary headline in cluster
                representative = cluster[0]
                similarity = fuzz.partial_ratio(article.title.lower(), representative.title.lower())
                token_similarity = fuzz.token_set_ratio(article.title.lower(), representative.title.lower())
                combined_score = max(similarity, token_similarity)

                if combined_score >= self.cluster_threshold:
                    matched_cluster = cluster
                    break

            if matched_cluster:
                matched_cluster.append(article)
            else:
                clusters.append([article])

        stories: List[Story] = []
        for cluster in clusters:
            primary = cluster[0]
            sources = list(dict.fromkeys([a.source for a in cluster]))
            topics = list(dict.fromkeys([t for a in cluster for t in a.topics]))

            story = Story(
                headline=primary.title,
                summary=primary.description or primary.content[:300],
                why_it_matters="",
                category=primary.category,
                articles=cluster,
                sources=sources,
                topics=topics
            )
            stories.append(story)

        logger.info(f"Clustering: Grouped {len(articles)} articles into {len(stories)} stories")
        return stories
