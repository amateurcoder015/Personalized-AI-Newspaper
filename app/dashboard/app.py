import logging
from pathlib import Path
from typing import List, Dict, Any
from app.database import DatabaseManager
from app.database.models import Edition

logger = logging.getLogger(__name__)


class DashboardApp:
    """Provides a lightweight web dashboard & archive reader for past editions."""

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
                "pdf_exists": Path(ed.pdf_path).exists() if ed.pdf_path else False
            })
        return archive_items
