import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.database import DatabaseManager
from app.database.models import Edition

logger = logging.getLogger(__name__)


class DashboardApp:
    """Provides a lightweight web dashboard, source health status view, and archive reader."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_archive_list(self) -> List[Dict[str, Any]]:
        editions = self.db.get_editions(limit=30)
        archive_items = []
        for ed in editions:
            archive_items.append({
                "edition_id": ed.edition_id,
                "date": ed.date,
                "generated_at": ed.generated_at,
                "stories_count": ed.stories_count,
                "html_path": ed.html_path,
                "pdf_path": ed.pdf_path,
                "html_exists": Path(ed.html_path).exists() if ed.html_path else False,
                "pdf_exists": Path(ed.pdf_path).exists() if ed.pdf_path else False,
                "run_log": ed.run_log,
                "source_health": ed.source_health
            })
        return archive_items

    def get_latest_run_summary(self) -> Optional[Dict[str, Any]]:
        latest = self.db.get_latest_edition()
        if not latest:
            return None
        return {
            "edition_id": latest.edition_id,
            "date": latest.date,
            "generated_at": latest.generated_at,
            "stories_count": latest.stories_count,
            "html_path": latest.html_path,
            "pdf_path": latest.pdf_path,
            "run_log": latest.run_log,
            "source_health": latest.source_health
        }
