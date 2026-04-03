# -*- coding: utf-8 -*-
"""
Base scraper class and shared utilities for all data sources.
"""

import hashlib
import logging
import re
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


def generate_id(text: str) -> str:
    """Generate a deterministic short ID from text."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def clean_text(text: str) -> str:
    """Remove excess whitespace, HTML tags, etc."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    SOURCE_NAME = "unknown"
    SOURCE_TYPE = "news"        # news / social / official
    SOURCE_WEIGHT = 0.5

    # Keywords to monitor
    KEYWORDS = [
        "香港保险", "港险", "GN16", "指引34", "分红实现率",
        "保诚", "友邦", "AIA", "安盛", "AXA", "宏利", "Manulife",
        "永明", "富通", "中国人寿海外", "中银人寿", "苏黎世", "忠意",
        "水滴", "蜗牛保", "慧择", "大象保险", "小雨伞",
        "理赔", "拒赔", "投诉", "监管", "保监局",
        "大湾区", "跨境", "内地客", "CRS", "RBC",
        "InsurTech", "保险科技",
    ]

    def __init__(self):
        self.session = None  # Subclasses may set up a requests.Session

    @abstractmethod
    def fetch_raw(self) -> list:
        """Fetch raw items from the source. Returns a list of dicts."""
        ...

    @abstractmethod
    def parse_item(self, raw_item: dict) -> dict | None:
        """Parse a single raw item into the unified schema.
        Return None to skip the item."""
        ...

    def get_news(self) -> list[dict]:
        """Main entry point: fetch + parse + filter."""
        try:
            raw_items = self.fetch_raw()
            logger.info("[%s] Fetched %d raw items", self.SOURCE_NAME, len(raw_items))
        except Exception as e:
            logger.error("[%s] Fetch failed: %s", self.SOURCE_NAME, e)
            return []

        results = []
        for raw in raw_items:
            try:
                item = self.parse_item(raw)
                if item and self._is_relevant(item):
                    item.setdefault("source", self.SOURCE_NAME)
                    item.setdefault("source_type", self.SOURCE_TYPE)
                    item.setdefault("source_weight", self.SOURCE_WEIGHT)
                    item.setdefault("scraped_at", datetime.now().isoformat())
                    if "id" not in item:
                        item["id"] = generate_id(item.get("title", ""))
                    results.append(item)
            except Exception as e:
                logger.warning("[%s] Parse error: %s", self.SOURCE_NAME, e)

        logger.info("[%s] Produced %d relevant items", self.SOURCE_NAME, len(results))
        return results

    def _is_relevant(self, item: dict) -> bool:
        """Check if the item matches our monitoring keywords."""
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        return any(kw.lower() in text for kw in self.KEYWORDS)
