import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from playwright.sync_api import sync_playwright

from app.database.models import (
    Story, MarketSnapshot, CommoditySnapshot, GithubRepo, CausalConnection
)
from app.newspaper.generator import NewspaperGenerator

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class PDFGenerator:
    """Renders modern editorial HTML newspaper to an 8-page A4 PDF using Playwright Chromium."""

    def __init__(self, output_dir: str = "data/editions"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.html_generator = NewspaperGenerator(output_dir=str(self.output_dir))

    def generate_pdf(
        self,
        top_stories: List[Story],
        sections: Dict[str, List[Story]],
        sector_stories: Dict[str, List[Story]],
        market_snapshots: List[MarketSnapshot],
        commodity_snapshots: List[CommoditySnapshot],
        commodity_drivers: Dict[str, str],
        github_repos: List[GithubRepo],
        causal_connections: List[CausalConnection],
        calendar_items: Dict[str, List[str]],
        finance_concept: Dict[str, Any],
        user_name: str = "Tony Stark"
    ) -> str:
        """Render newspaper HTML first, then print to PDF using Playwright Chromium."""
        today = datetime.now()
        date_formatted = today.strftime("%d %B %Y")
        edition_id = today.strftime("EDITION_%Y%m%d")
        pdf_path = self.output_dir / f"{edition_id}.pdf"
        named_pdf_path = self.output_dir / f"The Daily Brief — {date_formatted}.pdf"

        # 1. Render HTML edition using Jinja2 & Editorial CSS
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
            user_name=user_name
        )

        html_path = Path(edition.html_path).resolve()
        logger.info(f"HTML Newspaper rendered at {html_path}. Generating Playwright PDF...")

        # 2. Render to PDF via Playwright
        chrome_app_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with sync_playwright() as p:
                if os.path.exists(chrome_app_path):
                    context = p.chromium.launch_persistent_context(
                        tmpdir,
                        executable_path=chrome_app_path,
                        headless=True
                    )
                else:
                    context = p.chromium.launch_persistent_context(
                        tmpdir,
                        headless=True
                    )
                
                page = context.pages[0] if context.pages else context.new_page()
                file_url = f"file://{html_path}"
                page.goto(file_url, wait_until="networkidle")

                # Allow any web fonts / styles to stabilize
                page.wait_for_timeout(500)

                pdf_bytes = page.pdf(
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True
                )
                
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                
                with open(named_pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                
                context.close()

        logger.info(f"Playwright PDF generated successfully: {pdf_path} ({len(pdf_bytes)} bytes)")
        return str(pdf_path.resolve())
