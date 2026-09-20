import tempfile
from pathlib import Path
from app.database.models import Article, Story, MarketSnapshot, CommoditySnapshot, GithubRepo, CausalConnection
from app.newspaper.generator import NewspaperGenerator


def test_newspaper_rendering():
    with tempfile.TemporaryDirectory() as tmp_dir:
        generator = NewspaperGenerator(output_dir=tmp_dir)

        a1 = Article(title="TCS Reports Record Revenue", url="https://example.com/tcs", source="Economic Times")
        story = Story(
            headline="TCS Reports Record Revenue",
            summary="IT giant TCS delivered strong Q3 financial results.",
            why_it_matters="Demonstrates resilience in IT services export demand.",
            articles=[a1],
            sources=["Economic Times"]
        )

        top_stories = [story]
        sections = {"india": [], "markets": [], "companies": [], "technology": [], "global": []}
        sector_stories = {"Banking & Financial Services": [], "Information Technology": [story]}
        market_snapshots = [MarketSnapshot(name="NIFTY 50", value="22,500", change="+0.5%", is_positive=True)]
        commodity_snapshots = [CommoditySnapshot(name="Gold", price="₹72,000/10g", change="+0.2%", is_positive=True)]
        commodity_drivers = {"gold_driver": "Gold held steady.", "silver_driver": "Silver tracked demand."}
        github_repos = [GithubRepo(name="browser-use", description="AI Agent browser automation", category="AI", url="https://github.com/browser-use/browser-use")]
        causal_connections = [CausalConnection(title="Yields & Gold", premise="Yields rose", chain_steps=["Yields ↑", "USD ↑", "Gold pressure"], why_matters="Impacts gold pricing")]
        calendar_items = {"today": ["TCS Call"], "this_week": ["Fed Meeting"]}

        finance_concept = {
            "concept": "EBITDA Margin",
            "explanation": "Operating profitability metric measuring earnings before interest, tax, depreciation, and amortization.",
            "why_relevant_today": "TCS operational margins expanded 50 bps.",
            "numerical_example": "A firm with ₹1,000 Cr revenue and ₹250 Cr EBITDA has a 25% margin."
        }

        html_out, edition = generator.render_newspaper(
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
            user_name="Test User"
        )

        assert "The Daily Brief" in html_out
        assert "TCS Reports Record Revenue" in html_out
        assert "EBITDA Margin" in html_out
        assert "browser-use" in html_out
        assert "READ ORIGINAL →" in html_out or "READ →" in html_out or "Read original →" in html_out
        assert Path(edition.html_path).exists()
