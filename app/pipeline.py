import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.config import AppConfig, load_config
from app.database import DatabaseManager
from app.collectors import RSSCollector
from app.collectors.markets import MarketDataCollector
from app.collectors.commodities import CommodityCollector
from app.collectors.github import GithubCollector
from app.collectors.economic_calendar import EconomicCalendarCollector
from app.processing import ArticleCleaner, ArticleDeduplicator, StoryClusterer, StoryRanker, ChangeDetector
from app.llm import FreeLLMAPIProvider, GeminiProvider, LLMEditor
from app.llm.cache import LLMCache
from app.learning.concept_selector import ConceptSelector
from app.newspaper import NewspaperGenerator
from app.pdf import PDFGenerator
from app.delivery import EmailDelivery, WhatsAppDelivery

logger = logging.getLogger(__name__)


class NewspaperPipeline:
    """Orchestrates end-to-end 14-section Daily Executive Newspaper Pipeline (Milestones 7 & 8).
    Includes source health tracking, retries, Graceful LLM degradation, change detection,
    market intelligence explanations, evidence scoring, and Playwright PDF generation.
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.db = DatabaseManager(db_path=self.config.db_path)
        self.cache = LLMCache(db=self.db, enabled=self.config.llm_settings.cache_enabled)

        self.rss_collector = RSSCollector(
            sources=self.config.sources,
            max_per_source=20,
            request_timeout=10,
            max_retries=3
        )
        self.market_collector = MarketDataCollector(requested_markets=self.config.user.markets)
        self.commodity_collector = CommodityCollector()
        self.github_collector = GithubCollector(limit=self.config.newspaper.github_count)
        self.calendar_collector = EconomicCalendarCollector()

        self.cleaner = ArticleCleaner()
        self.deduplicator = ArticleDeduplicator()
        self.clusterer = StoryClusterer()
        self.ranker = StoryRanker(
            user_config=self.config.user,
            ranking_config=self.config.ranking
        )
        self.change_detector = ChangeDetector(major_move_threshold=1.0)
        self.concept_selector = ConceptSelector(
            db=self.db,
            avoid_recent_days=self.config.learning.avoid_recent_concepts_days
        )

        provider_name = self.config.llm_provider.lower()
        if provider_name == "gemini":
            self.llm_provider = GeminiProvider(
                base_url=self.config.llm_base_url,
                api_key=self.config.llm_api_key,
                model=self.config.llm_model,
                cache=self.cache
            )
        else:
            self.llm_provider = FreeLLMAPIProvider(
                base_url=self.config.llm_base_url,
                api_key=self.config.llm_api_key,
                model=self.config.llm_model,
                cache=self.cache
            )
        self.editor = LLMEditor(provider=self.llm_provider)
        self.html_generator = NewspaperGenerator(output_dir=self.config.editions_dir)
        self.pdf_generator = PDFGenerator(output_dir=self.config.editions_dir)
        self.email_delivery = EmailDelivery(config=self.config)
        self.whatsapp_delivery = WhatsAppDelivery(config=self.config)

    def run_pipeline(
        self,
        dry_run: bool = False,
        include_github: bool = True,
        force_send_email: bool = False,
        force_send_whatsapp: bool = False
    ) -> Dict[str, Any]:
        """Run complete 14-section daily newspaper pipeline with full reliability and intelligence."""
        start_time = time.time()
        start_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        logger.info("=" * 60)
        logger.info("STARTING MILESTONES 7 & 8 AI DAILY NEWSPAPER PIPELINE")
        logger.info(f"Execution Date: {datetime.now().strftime('%A, %d %B %Y')}")
        logger.info("=" * 60)

        # 1. Collect news articles & structured data (with retries & timeouts)
        raw_articles = self.rss_collector.collect()
        source_health = dict(self.rss_collector.source_health)

        if not raw_articles:
            logger.warning("WARNING: No live RSS articles collected. Retrieving recent stored articles from SQLite...")
            raw_articles = self.db.get_recent_articles(limit=50)

        market_snapshots = self.market_collector.collect()
        source_health["Market API"] = getattr(self.market_collector, "status", "✓ OK")

        commodity_snapshots = self.commodity_collector.collect()
        source_health["Commodity API"] = getattr(self.commodity_collector, "status", "✓ OK")

        calendar_items = self.calendar_collector.collect()
        source_health["Economic Calendar"] = "✓ OK"

        github_repos = []
        if include_github:
            github_repos = self.github_collector.collect()
            source_health["GitHub API"] = "✓ OK"
        else:
            source_health["GitHub API"] = "Skipped (Daily Run)"

        logger.info(f"Step 1: Collected {len(raw_articles)} articles, {len(market_snapshots)} markets, {len(github_repos)} repos")

        # 2. Clean & Deduplicate
        cleaned_articles = self.cleaner.clean_articles(raw_articles)
        unique_articles = self.deduplicator.deduplicate(cleaned_articles)

        # 3. Cluster & Rank Stories
        stories = self.clusterer.cluster_articles(unique_articles)
        ranked_stories = self.ranker.rank_stories(stories)
        selected_stories = ranked_stories[:self.config.newspaper.max_total_stories]

        # 4. Change Detection vs Previous Edition
        previous_edition = self.db.get_latest_edition()
        previous_stories = []
        if previous_edition:
            previous_stories = self.db.get_edition_stories(previous_edition.edition_id)

        change_analysis = self.change_detector.detect_changes(
            current_stories=selected_stories,
            current_markets=market_snapshots,
            current_commodities=commodity_snapshots,
            watchlist_companies=self.config.user.companies,
            previous_edition=previous_edition,
            previous_stories=previous_stories
        )
        what_changed = change_analysis["what_changed"]
        watchlist_changes = change_analysis["watchlist_changes"]
        major_moves = change_analysis["major_market_moves"]

        # 5. LLM Editorial Processing & Market Explanation
        top_stories, sections, sector_stories, causal_connections, commodity_drivers = self.editor.edit_stories(
            selected_stories,
            top_limit=self.config.newspaper.top_stories_limit,
            configured_sectors=self.config.user.sectors
        )

        headlines_summary = "\n".join([f"- {s.headline}" for s in selected_stories[:10]])
        market_drivers = []
        if change_analysis["requires_market_explanation"]:
            market_drivers = self.editor.generate_why_did_markets_move(major_moves, headlines_summary)

        # 6. Finance Concept Rotation & Editorial
        base_concept = self.concept_selector.select_concept(headlines_summary)
        finance_concept = self.editor.generate_finance_concept_editorial(base_concept, headlines_summary)
        source_health["LLM API"] = "✓ OK"

        # 7A. Render 14-Section HTML Newspaper
        html_content, edition = self.html_generator.render_newspaper(
            top_stories=top_stories,
            sections=sections,
            sector_stories=sector_stories,
            market_snapshots=market_snapshots,
            commodity_snapshots=commodity_snapshots,
            commodity_drivers=commodity_drivers,
            github_repos=github_repos,
            causal_connections=causal_connections,
            calendar_items=calendar_items,
            finance_concept=finance_concept,
            what_changed=what_changed,
            market_drivers=market_drivers,
            watchlist_changes=watchlist_changes,
            source_health=source_health,
            user_name=self.config.user.name
        )

        # 7B. Render 14-Section Playwright PDF Newspaper
        pdf_file_path = self.pdf_generator.generate_pdf(
            top_stories=top_stories,
            sections=sections,
            sector_stories=sector_stories,
            market_snapshots=market_snapshots,
            commodity_snapshots=commodity_snapshots,
            commodity_drivers=commodity_drivers,
            github_repos=github_repos,
            causal_connections=causal_connections,
            calendar_items=calendar_items,
            finance_concept=finance_concept,
            user_name=self.config.user.name
        )
        edition.pdf_path = pdf_file_path

        # 8. Delivery
        email_sent = False
        whatsapp_sent = False

        if (self.config.email_enabled or force_send_email) and not dry_run:
            email_sent = self.email_delivery.send_newspaper(html_content, pdf_path=pdf_file_path)

        if (self.config.whatsapp_enabled or force_send_whatsapp) and not dry_run:
            whatsapp_sent = self.whatsapp_delivery.send_notification(top_stories, edition.html_path)

        # Token & Usage Accounting
        usage_summary = self.cache.get_summary()

        elapsed_sec = round(time.time() - start_time, 2)
        run_log = {
            "execution_date": datetime.now().strftime("%d %B %Y"),
            "started_at": start_str,
            "duration_seconds": elapsed_sec,
            "articles_collected": len(raw_articles),
            "articles_after_filtering": len(cleaned_articles),
            "unique_story_clusters": len(stories),
            "selected_stories": len(selected_stories),
            "llm_calls": usage_summary["calls"],
            "input_tokens": usage_summary["input_tokens"],
            "output_tokens": usage_summary["output_tokens"],
            "cache_hits": usage_summary["cache_hits"],
            "estimated_cost": usage_summary["estimated_cost"],
            "pdf_status": "SUCCESS" if pdf_file_path else "FAILED",
            "email_status": "SUCCESS" if email_sent else ("SKIPPED" if dry_run else "FAILED"),
            "whatsapp_status": "SUCCESS" if whatsapp_sent else ("SKIPPED" if dry_run else "FAILED")
        }

        edition.run_log = run_log
        edition.source_health = source_health
        self.db.save_edition(edition)

        logger.info("=" * 60)
        logger.info("PIPELINE RUN COMPLETE")
        logger.info(f"Articles: {len(raw_articles)} | Stories: {len(selected_stories)} | Duration: {elapsed_sec}s")
        logger.info(f"LLM Calls: {usage_summary['calls']} | Tokens: In={usage_summary['input_tokens']}, Out={usage_summary['output_tokens']} | Cost: {usage_summary['estimated_cost']}")
        logger.info("=" * 60)

        return {
            "status": "success",
            "edition_id": edition.edition_id,
            "html_path": edition.html_path,
            "pdf_path": edition.pdf_path,
            "stories_count": edition.stories_count,
            "articles_collected": len(raw_articles),
            "source_health": source_health,
            "run_log": run_log,
            "usage_summary": usage_summary,
            "email_sent": email_sent,
            "whatsapp_sent": whatsapp_sent
        }
