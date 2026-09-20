import pytest
from typing import Optional, Dict, Any
from app.database.models import Article, Story, MarketSnapshot, CommoditySnapshot, Edition
from app.processing.change_detector import ChangeDetector
from app.collectors.rss import RSSCollector
from app.llm.editor import LLMEditor
from app.llm.base import LLMProvider


class MockFailingLLMProvider(LLMProvider):
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        raise Exception("Connection Refused / LLM Service Unavailable")

    def generate_structured(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        raise Exception("HTTP 500 / Malformed JSON Response")


def test_change_detector_deltas():
    detector = ChangeDetector(major_move_threshold=1.0)
    
    a1 = Article(title="Reliance Announces New Solar Gigafactory", url="https://example.com/rel", source="Reuters")
    story1 = Story(headline="Reliance Announces New Solar Gigafactory", summary="Reliance expands clean energy footprint.", articles=[a1])
    
    markets = [
        MarketSnapshot(name="NIFTY 50", value="25,750.40", change="+350.00 (+1.40%)", is_positive=True),
        MarketSnapshot(name="SENSEX", value="84,210.15", change="+200.00 (+0.24%)", is_positive=True)
    ]
    commodities = [
        CommoditySnapshot(name="Gold", price="₹1,12,450 / 10g", change="+0.42%", is_positive=True)
    ]
    
    res = detector.detect_changes(
        current_stories=[story1],
        current_markets=markets,
        current_commodities=commodities,
        watchlist_companies=["Reliance", "TCS"]
    )
    
    assert len(res["what_changed"]) > 0
    assert any("NIFTY 50" in b for b in res["what_changed"])
    assert res["requires_market_explanation"] is True
    assert "Reliance" in res["watchlist_changes"]


def test_llm_editor_fallback_on_failure():
    failing_provider = MockFailingLLMProvider()
    editor = LLMEditor(provider=failing_provider)
    
    a1 = Article(title="RBI Keeps Repo Rate at 6.5%", description="Central bank maintains monetary stance.", url="https://example.com/rbi", source="RBI Announcement", is_primary_source=True)
    story = Story(headline="RBI Keeps Repo Rate at 6.5%", summary="", articles=[a1], sources=["RBI Announcement"])
    
    processed = editor.process_story(story)
    
    assert processed.headline == "RBI Keeps Repo Rate at 6.5%"
    assert "Central bank maintains" in processed.summary
    assert processed.evidence_level == "HIGH CONFIDENCE"
    assert processed.is_primary_source is True


def test_rss_collector_resilience():
    # Test configured with unreachable URL
    sources = {"test": [{"name": "Broken Feed", "url": "http://127.0.0.1:9999/broken.xml"}]}
    collector = RSSCollector(sources=sources, max_per_source=5, request_timeout=1, max_retries=1)
    
    articles = collector.collect()
    
    assert len(articles) == 0
    assert "Broken Feed" in collector.source_health
    assert "WARNING" in collector.source_health["Broken Feed"]
