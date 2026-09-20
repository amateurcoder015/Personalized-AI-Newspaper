import logging
from typing import Dict, Set
from app.database.models import Story

logger = logging.getLogger(__name__)

SECTOR_KEYWORDS: Dict[str, Set[str]] = {
    "Banking & Financial Services": {
        "bank", "banking", "rbi", "nbfc", "hdfc", "icici", "sbi", "loan", "credit", "npa", "deposit", "mortgage", "fintech"
    },
    "Information Technology": {
        "tcs", "infosys", "wipro", "hcl", "software", "it services", "tech", "saas", "cloud", "developer", "ai", "cybersecurity"
    },
    "Healthcare & Pharma": {
        "pharma", "drug", "fda", "hospital", "healthcare", "vaccine", "biotech", "clinical", "medicine"
    },
    "Automobiles": {
        "auto", "ev", "electric vehicle", "tata motors", "maruti", "mahindra", "car", "suv", "battery", "tesla"
    },
    "Power & Utilities": {
        "power", "utility", "grid", "electricity", "solar", "renewable", "thermal", "wind", "ntpc", "adanipower"
    },
    "Industrials": {
        "industrial", "manufacturing", "machinery", "engineering", "l&t", "defense", "aerospace", "factory"
    },
    "Infrastructure": {
        "infrastructure", "highway", "port", "railway", "construction", "cement", "airport", "logistics"
    },
    "Telecom": {
        "telecom", "5g", "spectrum", "jio", "airtel", "vodafone", "broadband", "mobile"
    },
    "FMCG": {
        "fmcg", "consumer", "retail", "hul", "nestle", "itc", "packaged goods", "supermarket"
    },
    "Energy": {
        "energy", "oil", "gas", "crude", "refinery", "reliance", "ongc", "bpcl", "petroleum"
    },
    "Metals & Mining": {
        "metal", "steel", "mining", "copper", "iron ore", "aluminum", "tata steel", "coal", "gold", "silver"
    },
    "Real Estate": {
        "real estate", "housing", "property", "dlf", "builder", "commercial", "reit"
    },
    "Chemicals": {
        "chemical", "fertilizer", "specialty chemical", "agrochemical"
    }
}


class SectorClassifier:
    """Rule-based programmatic sector classifier."""

    @staticmethod
    def classify_story(story: Story) -> str:
        text = f"{story.headline} {story.summary}".lower()

        for sector, keywords in SECTOR_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return sector
        return "General"
