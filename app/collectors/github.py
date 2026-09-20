import logging
import requests
from typing import List
from app.database.models import GithubRepo

logger = logging.getLogger(__name__)


class GithubCollector:
    """Searches GitHub API for trending/popular projects in AI, LLMs, Agents, FinTech, and Quant Finance."""

    def __init__(self, limit: int = 5):
        self.limit = limit

    def collect(self) -> List[GithubRepo]:
        repos: List[GithubRepo] = []
        try:
            # Search GitHub for trending AI/Fintech repos via GitHub REST API
            url = "https://api.github.com/search/repositories?q=topic:ai-agent+OR+topic:llm+OR+topic:quantitative-finance&sort=stars&order=desc&per_page=10"
            headers = {"User-Agent": "Personal-AI-Newspaper/1.0"}
            response = requests.get(url, headers=headers, timeout=8)

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])[:self.limit]
                for item in items:
                    repos.append(GithubRepo(
                        name=item.get("name", "Repository"),
                        description=item.get("description", "") or "No description provided.",
                        why_interesting="Notable open-source project with active community development.",
                        category="AI & Developer Tools",
                        url=item.get("html_url", "https://github.com"),
                        stars=item.get("stargazers_count", 0),
                        language=item.get("language", "Python") or "Python"
                    ))
            else:
                logger.warning(f"GitHub API returned HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to fetch GitHub API repos ({e}). Using curated fallback projects.")

        if not repos:
            # Curated quality fallback projects
            repos = [
                GithubRepo(
                    name="browser-use",
                    description="Make websites accessible for AI agents with automated browser control.",
                    why_interesting="Enables LLM agents to interact seamlessly with dynamic web interfaces.",
                    category="AI & Agents",
                    url="https://github.com/browser-use/browser-use",
                    stars=18500,
                    language="Python"
                ),
                GithubRepo(
                    name="finrl",
                    description="Open-source framework for quantitative finance using reinforcement learning.",
                    why_interesting="Provides modular RL algorithms tailored for algorithmic trading and portfolio optimization.",
                    category="Quantitative Finance",
                    url="https://github.com/AI4Finance-Foundation/FinRL",
                    stars=11200,
                    language="Python"
                ),
                GithubRepo(
                    name="autogen",
                    description="Framework for building multi-agent AI conversations and workflows.",
                    why_interesting="Simplifies orchestrating multi-agent systems to solve complex developer and analytical tasks.",
                    category="AI Frameworks",
                    url="https://github.com/microsoft/autogen",
                    stars=34000,
                    language="Python"
                )
            ]
        return repos[:self.limit]
