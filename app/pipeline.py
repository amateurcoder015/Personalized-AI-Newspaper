import logging
from typing import Dict, Any, Optional
from app.config import AppConfig, load_config
from app.database import DatabaseManager
from app.collectors import RSSCollector
from app.collectors.markets import MarketDataCollector
from app.collectors.commodities import CommodityCollector
from app.collectors.github import GithubCollector
from app.collectors.economic_calendar import EconomicCalendarCollector
from app.processing import ArticleCleaner, ArticleDeduplicator, StoryClusterer, StoryRanker
from app.llm import FreeLLMAPIProvider, LLMEditor
from app.llm.cache import LLMCache
from app.learning.concept_selector import ConceptSelector
from app.newspaper import NewspaperGenerator
from app.pdf import PDFGenerator
from app.delivery import EmailDelivery, WhatsAppDelivery

logger = logging.getLogger(__name__)


class NewspaperPipeline:
    """Orchestrates end-to-end 12-section Daily Executive Newspaper Pipeline (HTML + PDF)."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.db = DatabaseManager(db_path=self.config.db_path)
        self.cache = LLMCache(db=self.db, enabled=self.config.llm_settings.cache_enabled)

        self.rss_collector = RSSCollector(
            sources=self.config.sources,
            max_per_source=20
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
        self.concept_selector = ConceptSelector(
            db=self.db,
            avoid_recent_days=self.config.learning.avoid_recent_concepts_days
        )

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
        """Run complete 12-section daily newspaper pipeline (HTML + PDF)."""
        logger.info("=" * 60)
        logger.info("STARTING EXPANDED 12-SECTION AI DAILY NEWSPAPER PIPELINE")
        logger.info("=" * 60)

        # 1. Collect news articles & structured data
        raw_articles = self.rss_collector.collect()
        if not raw_articles:
            logger.warning("No RSS articles collected. Retrieving recent articles from SQLite...")
            raw_articles = self.db.get_recent_articles(limit=50)

        market_snapshots = self.market_collector.collect()
        commodity_snapshots = self.commodity_collector.collect()
        calendar_items = self.calendar_collector.collect()
        github_repos = self.github_collector.collect() if include_github else []

        logger.info(f"Step 1: Collected {len(raw_articles)} articles, {len(market_snapshots)} markets, {len(github_repos)} repos")

        # 2. Clean & Deduplicate
        cleaned_articles = self.cleaner.clean_articles(raw_articles)
        unique_articles = self.deduplicator.deduplicate(cleaned_articles)

        # 3. Cluster stories
        stories = self.clusterer.cluster_articles(unique_articles)

        # 4. Rank stories
        ranked_stories = self.ranker.rank_stories(stories)
        selected_stories = ranked_stories[:self.config.newspaper.max_total_stories]

        # 5. LLM Editorial Processing across 12 sections
        top_stories, sections, sector_stories, causal_connections, commodity_drivers = self.editor.edit_stories(
            selected_stories,
            top_limit=self.config.newspaper.top_stories_limit,
            configured_sectors=self.config.user.sectors
        )

        # 6. Finance Concept Learning Rotation Selection
        headlines_summary = "\n".join([f"- {s.headline}" for s in selected_stories[:10]])
        base_concept = self.concept_selector.select_concept(headlines_summary)
        finance_concept = self.editor.generate_finance_concept_editorial(base_concept, headlines_summary)

        # 7A. Render 12-Section HTML Newspaper
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
            user_name=self.config.user.name
        )

        # 7B. Render 12-Section Premium PDF Newspaper
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
        self.db.save_edition(edition)

        logger.info(f"Step 7: Rendered HTML ({edition.html_path}) and PDF ({edition.pdf_path})")

        # 8. Delivery
        email_sent = False
        whatsapp_sent = False

        if (self.config.email_enabled or force_send_email) and not dry_run:
            email_sent = self.email_delivery.send_newspaper(html_content, pdf_path=pdf_file_path)

        if (self.config.whatsapp_enabled or force_send_whatsapp) and not dry_run:
            whatsapp_sent = self.whatsapp_delivery.send_notification(top_stories, edition.html_path)

        # Token Usage Accounting
        usage_summary = self.cache.get_summary()

        logger.info("=" * 60)
        logger.info("LLM TOKEN & COST USAGE")
        logger.info(f"Calls: {usage_summary['calls']} | Input Tokens: {usage_summary['input_tokens']} | Output Tokens: {usage_summary['output_tokens']} | Cache Hits: {usage_summary['cache_hits']} | Estimated Cost: {usage_summary['estimated_cost']}")
        logger.info("=" * 60)

        return {
            "status": "success",
            "edition_id": edition.edition_id,
            "html_path": edition.html_path,
            "pdf_path": edition.pdf_path,
            "stories_count": edition.stories_count,
            "usage_summary": usage_summary,
            "email_sent": email_sent,
            "whatsapp_sent": whatsapp_sent
        }
