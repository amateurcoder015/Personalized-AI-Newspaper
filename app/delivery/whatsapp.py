import logging
from typing import List, Optional
import requests
from app.config import AppConfig
from app.database.models import Story

logger = logging.getLogger(__name__)


class WhatsAppDelivery:
    """Optional WhatsApp notification delivery."""

    def __init__(self, config: AppConfig):
        self.config = config

    def send_notification(self, top_stories: List[Story], edition_url: Optional[str] = None) -> bool:
        if not self.config.whatsapp_enabled:
            logger.info("WhatsApp delivery is disabled in configuration.")
            return False

        if not self.config.whatsapp_api_key or not self.config.whatsapp_recipient:
            logger.warning("WhatsApp API key or recipient missing in config.")
            return False

        # Format brief notification summary
        top_headline = top_stories[0].headline if top_stories else "Daily Brief Ready"
        msg = f"📰 YOUR DAILY BRIEF\n\nGood morning! Today's newspaper is ready.\n\n🔥 Top Story: {top_headline}\n"
        if edition_url:
            msg += f"\n📖 Read full edition: {edition_url}"

        logger.info(f"WhatsApp notification message prepared for {self.config.whatsapp_recipient}")
        # Placeholder for external Twilio / WhatsApp Cloud API call
        return True
