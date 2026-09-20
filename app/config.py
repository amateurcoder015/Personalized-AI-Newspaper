import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class UserConfig(BaseModel):
    name: str = "User"
    interests: List[str] = Field(default_factory=list)
    companies: List[str] = Field(default_factory=list)
    markets: List[str] = Field(default_factory=list)
    sectors: List[str] = Field(default_factory=list)


class NewspaperConfig(BaseModel):
    top_stories_limit: int = 5
    max_total_stories: int = 25
    target_reading_minutes: int = 15
    github_finds_enabled: bool = True
    github_count: int = 5


class LLMConfig(BaseModel):
    max_daily_calls: int = 15
    cache_enabled: bool = True
    max_article_words: int = 800
    batch_processing: bool = True


class LearningConfig(BaseModel):
    finance_concept: bool = True
    max_concept_words: int = 250
    avoid_recent_concepts_days: int = 30


class RankingConfig(BaseModel):
    watchlist_match_weight: float = 3.0
    major_event_weight: float = 3.0
    multiple_sources_weight: float = 2.0
    recency_weight: float = 2.0
    market_impact_weight: float = 2.0
    topic_match_weight: float = 1.0
    global_importance_weight: float = 0.55
    personal_relevance_weight: float = 0.45


class SourceItem(BaseModel):
    name: str
    url: str


class AppConfig(BaseModel):
    user: UserConfig
    newspaper: NewspaperConfig
    sections: Dict[str, bool] = Field(default_factory=dict)
    llm_settings: LLMConfig = Field(default_factory=LLMConfig)
    learning: LearningConfig = Field(default_factory=LearningConfig)
    ranking: RankingConfig = Field(default_factory=RankingConfig)
    sources: Dict[str, List[SourceItem]] = Field(default_factory=dict)

    # Environment variables
    llm_provider: str = os.getenv("LLM_PROVIDER", "freellmapi")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    email_enabled: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    email_provider: str = os.getenv("EMAIL_PROVIDER", "smtp")
    email_smtp_server: str = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    email_smtp_port: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    email_address: str = os.getenv("EMAIL_ADDRESS", "")
    email_app_password: str = os.getenv("EMAIL_APP_PASSWORD", "")
    email_recipient: str = os.getenv("EMAIL_RECIPIENT", "")

    whatsapp_enabled: bool = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
    whatsapp_api_key: str = os.getenv("WHATSAPP_API_KEY", "")
    whatsapp_phone_number: str = os.getenv("WHATSAPP_PHONE_NUMBER", "")
    whatsapp_recipient: str = os.getenv("WHATSAPP_RECIPIENT", "")

    newspaper_time: str = os.getenv("NEWSPAPER_TIME", "07:00")
    db_path: str = os.getenv("DB_PATH", "data/newspaper.db")
    editions_dir: str = os.getenv("EDITIONS_DIR", "data/editions")


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from config.yaml and environment variables."""
    if config_path is None:
        config_path = str(BASE_DIR / "config.yaml")

    yaml_data: Dict[str, Any] = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

    user_cfg = UserConfig(**yaml_data.get("user", {}))
    
    np_raw = yaml_data.get("newspaper", {}).get("daily", {})
    np_raw_w = yaml_data.get("newspaper", {}).get("weekly", {})
    newspaper_cfg = NewspaperConfig(
        top_stories_limit=np_raw.get("top_stories", 5),
        max_total_stories=np_raw.get("max_total_stories", 25),
        target_reading_minutes=np_raw.get("target_reading_minutes", 15),
        github_finds_enabled=np_raw_w.get("github_finds", True),
        github_count=np_raw_w.get("github_count", 5)
    )

    sections_cfg = yaml_data.get("sections", {})
    llm_cfg = LLMConfig(**yaml_data.get("llm", {}))
    learning_cfg = LearningConfig(**yaml_data.get("learning", {}))
    ranking_cfg = RankingConfig(**yaml_data.get("ranking", {}))

    sources_raw = yaml_data.get("sources", {})
    sources_dict: Dict[str, List[SourceItem]] = {}
    for cat, items in sources_raw.items():
        sources_dict[cat] = [SourceItem(**item) for item in items]

    return AppConfig(
        user=user_cfg,
        newspaper=newspaper_cfg,
        sections=sections_cfg,
        llm_settings=llm_cfg,
        learning=learning_cfg,
        ranking=ranking_cfg,
        sources=sources_dict
    )
