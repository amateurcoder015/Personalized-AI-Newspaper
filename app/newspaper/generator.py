import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from jinja2 import Environment, FileSystemLoader
from app.database.models import (
    Story, MarketSnapshot, CommoditySnapshot, GithubRepo, CausalConnection, Edition
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class NewspaperGenerator:
    """Renders 12-section HTML executive daily newspaper using Jinja2 templates."""

    def __init__(self, template_dir: Optional[str] = None, output_dir: str = "data/editions"):
        if template_dir is None:
            template_dir = str(BASE_DIR / "app" / "newspaper" / "templates")
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def render_newspaper(
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
    ) -> Tuple[str, Edition]:
        """Render newspaper HTML and save to editions directory."""
        css_path = BASE_DIR / "app" / "newspaper" / "static" / "style.css"
        css_styles = ""
        if css_path.exists():
            with open(css_path, "r", encoding="utf-8") as f:
                css_styles = f.read()

        today = datetime.now()
        date_str = today.strftime("%A, %d %B %Y")
        year_str = str(today.year)
        edition_id = today.strftime("EDITION_%Y%m%d")

        template = self.env.get_template("newspaper.html")
        html_out = template.render(
            date_str=date_str,
            year_str=year_str,
            user_name=user_name,
            edition_num=today.strftime("%j"),
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
            css_styles=css_styles
        )

        out_file = self.output_dir / f"{edition_id}.html"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_out)

        total_stories = len(top_stories) + sum(len(v) for v in sections.values())
        edition = Edition(
            edition_id=edition_id,
            date=date_str,
            html_path=str(out_file.resolve()),
            status="generated",
            stories_count=total_stories
        )

        logger.info(f"12-Section Newspaper rendered successfully: {out_file.resolve()} ({total_stories} stories)")
        return html_out, edition
