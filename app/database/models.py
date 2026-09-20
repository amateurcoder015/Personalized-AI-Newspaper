import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Article(BaseModel):
    id: str = ""
    title: str
    description: str = ""
    content: str = ""
    url: str
    source: str
    author: str = ""
    published_at: str = ""
    category: str = "general"
    sector: str = "General"
    image_url: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    hash: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def model_post_init(self, __context):
        if not self.hash:
            self.hash = hashlib.md5(self.url.encode("utf-8")).hexdigest()
        if not self.id:
            self.id = self.hash


class Story(BaseModel):
    id: str = ""
    headline: str
    summary: str = ""
    why_it_matters: str = ""
    category: str = "top_stories"
    sector: str = "General"
    importance_score: float = 0.0
    relevance_score: float = 0.0
    final_score: float = 0.0
    articles: List[Article] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    matched_watchlist: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def model_post_init(self, __context):
        if not self.id:
            raw = f"{self.headline}_{self.created_at}"
            self.id = hashlib.md5(raw.encode("utf-8")).hexdigest()


class MarketSnapshot(BaseModel):
    name: str
    value: str
    change: str
    is_positive: Optional[bool] = None


class CommoditySnapshot(BaseModel):
    name: str
    price: str
    change: str
    is_positive: Optional[bool] = None
    driver_analysis: str = ""


class GithubRepo(BaseModel):
    name: str
    description: str
    why_interesting: str = ""
    category: str = "AI"
    url: str
    stars: int = 0
    language: str = "Python"


class CausalConnection(BaseModel):
    title: str
    premise: str
    chain_steps: List[str] = Field(default_factory=list)
    why_matters: str = ""


class LLMUsageLog(BaseModel):
    date: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0
    estimated_cost: float = 0.0


class ConceptUsage(BaseModel):
    concept: str
    used_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    related_story: str = ""


class Edition(BaseModel):
    edition_id: str
    date: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    html_path: str
    pdf_path: str = ""
    status: str = "generated"
    stories_count: int = 0
