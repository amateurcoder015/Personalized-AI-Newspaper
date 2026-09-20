import logging
from typing import List
from app.database.models import CommoditySnapshot

logger = logging.getLogger(__name__)


class CommodityCollector:
    """Collects precious metals (Gold & Silver) prices and daily changes."""

    def collect(self) -> List[CommoditySnapshot]:
        return [
            CommoditySnapshot(
                name="Gold",
                price="Data unavailable",
                change="",
                is_positive=None,
                driver_analysis=""
            ),
            CommoditySnapshot(
                name="Silver",
                price="Data unavailable",
                change="",
                is_positive=None,
                driver_analysis=""
            )
        ]
