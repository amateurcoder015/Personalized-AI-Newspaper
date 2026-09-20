import logging
from typing import List, Dict, Any, Tuple
from app.llm.base import LLMProvider
from app.llm.prompts import (
    SYSTEM_EDITORIAL_PROMPT,
    ARTICLE_SUMMARIZE_PROMPT,
    STORY_SYNTHESIS_PROMPT,
    GOLD_SILVER_DRIVER_PROMPT,
    CONNECT_DOTS_PROMPT,
    FINANCE_CONCEPT_PROMPT
)
from app.database.models import Story, CausalConnection
from app.processing.sector_classifier import SectorClassifier

logger = logging.getLogger(__name__)


class LLMEditor:
    """Editorial AI engine that refines stories, assigns sections, generates Gold/Silver drivers,
    Connect the Dots causal chains, market move explanations, and Finance Concept explanations.
    Uses purely factual source text fallback when LLM API fails or returns invalid JSON.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def process_story(self, story: Story) -> Story:
        """Use LLM to synthesize multi-article story or generate crisp summary & why-it-matters."""
        story.sector = SectorClassifier.classify_story(story)

        # Build sources with URLs for transparency
        sources_urls = []
        for a in story.articles:
            if a.source and a.url:
                sources_urls.append({"name": a.source, "url": a.url})
        story.sources_with_urls = sources_urls

        # Evidence level & primary source indicator
        has_primary = any(a.is_primary_source for a in story.articles)
        story.is_primary_source = has_primary

        if len(story.articles) >= 2 or has_primary:
            story.evidence_level = "HIGH CONFIDENCE"
        elif len(story.articles) == 1:
            story.evidence_level = "MEDIUM CONFIDENCE"
        else:
            story.evidence_level = "DEVELOPING"

        try:
            if len(story.articles) > 1:
                articles_text = ""
                for idx, a in enumerate(story.articles[:3], 1):
                    desc = (a.description or a.content)[:400]
                    articles_text += f"\n[{idx}] {a.title} ({a.source}): {desc}"

                prompt = STORY_SYNTHESIS_PROMPT.format(articles_text=articles_text)
                res = self.provider.generate_structured(prompt, system_prompt=SYSTEM_EDITORIAL_PROMPT)

                if res:
                    story.headline = res.get("headline", story.headline)
                    story.summary = res.get("summary", story.summary)
                    story.why_it_matters = res.get("why_it_matters", "")
                    if "category" in res and res["category"] in ["top_stories", "india", "markets", "companies", "technology", "global"]:
                        story.category = res["category"]
                else:
                    self._apply_factual_fallback(story)

            else:
                primary = story.articles[0] if story.articles else None
                title = primary.title if primary else story.headline
                content = (primary.description or primary.content)[:600] if primary else story.summary[:600]

                prompt = ARTICLE_SUMMARIZE_PROMPT.format(
                    title=title,
                    source=primary.source if primary else "News",
                    published_at=primary.published_at if primary else "Today",
                    content=content
                )
                res = self.provider.generate_structured(prompt, system_prompt=SYSTEM_EDITORIAL_PROMPT)

                if res:
                    story.summary = res.get("summary", title)
                    story.why_it_matters = res.get("why_it_matters", "")
                else:
                    self._apply_factual_fallback(story)

        except Exception as e:
            logger.warning(f"LLM process_story failed for '{story.headline[:40]}' ({e}). Using factual source fallback.")
            self._apply_factual_fallback(story)

        return story

    def _apply_factual_fallback(self, story: Story) -> None:
        """Apply strictly factual source headline and description without inventing AI text."""
        if story.articles:
            primary = story.articles[0]
            if primary.description:
                story.summary = primary.description
            elif primary.content:
                story.summary = primary.content[:300]
            else:
                story.summary = primary.title
        elif not story.summary:
            story.summary = story.headline

        # Clear invented why_it_matters on fallback
        story.why_it_matters = ""

    def assign_section(self, story: Story) -> str:
        text = f"{story.headline} {story.summary}".lower()

        if any(w in text for w in ["open-source", "openai", "nvidia", "microsoft", "google", "anthropic", "llm", "ai", "github", "software", "tech"]):
            return "technology"
        elif any(w in text for w in ["reliance", "hdfc", "tcs", "infosys", "apple", "alphabet", "earnings", "m&a", "ipo", "acquisition", "funding"]):
            return "companies"
        elif any(w in text for w in ["nifty", "sensex", "nasdaq", "bonds", "g-sec", "yield", "rupee", "usd", "forex", "gold", "silver"]):
            return "markets"
        elif any(w in text for w in ["rbi", "gdp", "inflation", "fiscal", "repo rate", "india", "budget", "tax", "gst"]):
            return "india"
        elif any(w in text for w in ["us fed", "china", "eu", "global trade", "central banks", "imf", "world bank"]):
            return "global"
        else:
            return story.category or "india"

    def generate_why_did_markets_move(self, major_moves: List[Dict[str, Any]], headlines_summary: str) -> List[str]:
        """Generate prudent market drivers using non-dogmatic phrasing. Return [] if LLM fails."""
        if not major_moves:
            return []

        move_names = ", ".join([f"{m['name']} ({m['change']})" for m in major_moves])
        prompt = (
            f"Major financial market movements occurred today: {move_names}.\n"
            f"Here is today's headline context:\n{headlines_summary}\n\n"
            f"Provide 3 concise market driver explanations using prudent, non-dogmatic phrasing "
            f"such as 'Reported drivers include...', 'Market commentary points to...', or 'The move coincided with...'.\n"
            f"Return JSON format:\n"
            f'{{"drivers": ["Driver 1...", "Driver 2...", "Driver 3..."]}}'
        )

        try:
            res = self.provider.generate_structured(prompt, system_prompt=SYSTEM_EDITORIAL_PROMPT)
            drivers = res.get("drivers", [])
            if isinstance(drivers, list) and len(drivers) > 0:
                return drivers[:3]
        except Exception as e:
            logger.warning(f"LLM generate_why_did_markets_move failed ({e}). Returning empty drivers list.")

        return []

    def edit_stories(
        self,
        stories: List[Story],
        top_limit: int = 5,
        configured_sectors: List[str] = None
    ) -> Tuple[List[Story], Dict[str, List[Story]], Dict[str, List[Story]], List[CausalConnection], Dict[str, str]]:
        """Process stories and divide into sections without duplicate story repetition."""
        edited_stories: List[Story] = []

        for s in stories:
            processed = self.process_story(s)
            edited_stories.append(processed)

        # 1. TOP Stories Section
        top_stories = edited_stories[:top_limit]
        top_ids = {s.id for s in top_stories}

        # Remaining stories
        remaining = [s for s in edited_stories if s.id not in top_ids]

        # 2. Main Sections
        sections: Dict[str, List[Story]] = {
            "india": [],
            "markets": [],
            "companies": [],
            "technology": [],
            "global": []
        }

        # 3. Sector Watch buckets
        sector_stories: Dict[str, List[Story]] = {}
        target_sectors = configured_sectors or [
            "Banking & Financial Services", "Information Technology", "Healthcare & Pharma",
            "Automobiles", "Power & Utilities", "Industrials"
        ]
        for sec in target_sectors:
            sector_stories[sec] = []

        for s in remaining:
            sec = self.assign_section(s)
            s.category = sec
            if sec in sections:
                sections[sec].append(s)
            else:
                sections["india"].append(s)

            if s.sector in sector_stories:
                if len(sector_stories[s.sector]) < 3:
                    sector_stories[s.sector].append(s)

        # Generate Commodity Drivers & Connect the Dots
        headlines_summary = "\n".join([f"- {s.headline}" for s in edited_stories[:10]])
        commodity_drivers = self.generate_gold_silver_drivers(headlines_summary)
        causal_connections = self.generate_connect_the_dots(headlines_summary)

        return top_stories, sections, sector_stories, causal_connections, commodity_drivers

    def generate_gold_silver_drivers(self, headlines_summary: str) -> Dict[str, str]:
        try:
            prompt = GOLD_SILVER_DRIVER_PROMPT.format(headlines_summary=headlines_summary)
            res = self.provider.generate_structured(prompt, system_prompt=SYSTEM_EDITORIAL_PROMPT)
            if res and ("gold_driver" in res or "silver_driver" in res):
                return {
                    "gold_driver": res.get("gold_driver", ""),
                    "silver_driver": res.get("silver_driver", "")
                }
        except Exception as e:
            logger.warning(f"LLM generate_gold_silver_drivers failed ({e}). Returning empty drivers.")

        return {"gold_driver": "", "silver_driver": ""}

    def generate_connect_the_dots(self, headlines_summary: str) -> List[CausalConnection]:
        try:
            prompt = CONNECT_DOTS_PROMPT.format(headlines_summary=headlines_summary)
            res = self.provider.generate_structured(prompt, system_prompt=SYSTEM_EDITORIAL_PROMPT)

            raw_connections = res.get("connections", [])
            connections = []
            if isinstance(raw_connections, list):
                for c in raw_connections:
                    connections.append(CausalConnection(
                        title=c.get("title", "Yield Movements & Emerging Market Assets"),
                        premise=c.get("premise", "Shifting rate expectations influenced yields and currencies."),
                        chain_steps=c.get("chain_steps", ["US Yields ↑", "Dollar Index ↑", "EM Currencies ↓", "Gold / India Impact"]),
                        why_matters=c.get("why_matters", "Monetary policy stance propagates through FX and asset valuations.")
                    ))
            if connections:
                return connections
        except Exception as e:
            logger.warning(f"LLM generate_connect_the_dots failed ({e}). Returning empty causal connections.")

        return []

    def generate_finance_concept_editorial(self, chosen_concept: Dict[str, Any], headlines_summary: str) -> Dict[str, Any]:
        try:
            prompt = FINANCE_CONCEPT_PROMPT.format(
                concept_title=chosen_concept["concept"],
                base_explanation=chosen_concept["explanation"],
                numerical_example=chosen_concept["numerical_example"],
                headlines_summary=headlines_summary
            )
            res = self.provider.generate_structured(prompt, system_prompt=SYSTEM_EDITORIAL_PROMPT)

            if res and "concept" in res:
                return {
                    "concept": res.get("concept", chosen_concept["concept"]),
                    "explanation": res.get("explanation", chosen_concept["explanation"]),
                    "why_relevant_today": res.get("why_relevant_today", "Today's developments illustrate how this concept impacts asset pricing."),
                    "numerical_example": res.get("numerical_example", chosen_concept["numerical_example"])
                }
        except Exception as e:
            logger.warning(f"LLM generate_finance_concept_editorial failed ({e}). Returning base concept data.")

        return {
            "concept": chosen_concept["concept"],
            "explanation": chosen_concept["explanation"],
            "why_relevant_today": "Today's developments illustrate how this concept impacts asset pricing.",
            "numerical_example": chosen_concept["numerical_example"]
        }

