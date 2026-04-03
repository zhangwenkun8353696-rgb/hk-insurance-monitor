# -*- coding: utf-8 -*-
"""
Official / institutional source scrapers — HK IA, Google News, RSS feeds.
"""

import re
import logging
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote

from .base import BaseScraper, clean_text, generate_id

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class HKIAScraper(BaseScraper):
    """Scrape Hong Kong Insurance Authority press releases."""

    SOURCE_NAME = "香港保监局"
    SOURCE_TYPE = "official"
    SOURCE_WEIGHT = 0.95

    def fetch_raw(self) -> list:
        items = []
        urls = [
            "https://www.ia.org.hk/sc/infocenter/press_releases.html",
            "https://www.ia.org.hk/en/infocenter/press_releases.html",
        ]
        for page_url in urls:
            try:
                resp = requests.get(page_url, headers=HEADERS, timeout=15)
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")
                rows = soup.select("table tr") or soup.select("div.press-release-item") or soup.select("li a")
                for row in rows:
                    items.append({"html": row, "base_url": page_url})
                logger.info("[HKIA] Fetched %d items from %s", len(rows), page_url)
            except Exception as e:
                logger.warning("[HKIA] Fetch failed for %s: %s", page_url, e)
        return items

    def parse_item(self, raw_item: dict) -> dict | None:
        html = raw_item["html"]
        links = html.select("a[href]")
        if not links:
            return None

        a = links[0]
        title = clean_text(a.get_text())
        href = a.get("href", "")
        if not title or len(title) < 5:
            return None

        if href and not href.startswith("http"):
            base = raw_item.get("base_url", "https://www.ia.org.hk")
            if href.startswith("/"):
                href = "https://www.ia.org.hk" + href
            else:
                href = base.rsplit("/", 1)[0] + "/" + href

        # Try to extract date from the row
        date_text = ""
        tds = html.select("td")
        if tds:
            for td in tds:
                td_text = clean_text(td.get_text())
                if re.search(r"\d{4}", td_text) and re.search(r"\d{1,2}", td_text):
                    date_text = td_text
                    break

        return {
            "id": generate_id(title + href),
            "title": title,
            "summary": title,  # Press releases typically need click-through for details
            "source": self.SOURCE_NAME,
            "url": href,
            "published": date_text or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }


class GoogleNewsScraper(BaseScraper):
    """Scrape Google News RSS for HK insurance topics."""

    SOURCE_NAME = "Google News"
    SOURCE_TYPE = "news"
    SOURCE_WEIGHT = 0.80

    SEARCH_QUERIES = [
        "香港保险",
        "Hong Kong insurance",
        "HK insurance regulation",
        "港险 大湾区",
    ]

    def fetch_raw(self) -> list:
        items = []
        for query in self.SEARCH_QUERIES:
            try:
                rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
                feed = feedparser.parse(rss_url)
                for entry in feed.entries:
                    items.append(entry)
                logger.info("[GoogleNews] Query '%s' got %d entries", query, len(feed.entries))
            except Exception as e:
                logger.warning("[GoogleNews] Query '%s' failed: %s", query, e)
        return items

    def parse_item(self, raw_item) -> dict | None:
        title = raw_item.get("title", "")
        link = raw_item.get("link", "")
        summary = raw_item.get("summary", "") or raw_item.get("description", "")
        published = raw_item.get("published", "")
        source = raw_item.get("source", {}).get("title", "") if hasattr(raw_item.get("source", {}), "get") else ""

        title = clean_text(title)
        summary = clean_text(summary)

        if not title or len(title) < 5:
            return None

        return {
            "id": generate_id(title + link),
            "title": title,
            "summary": summary[:500] if summary else title,
            "source": source or self.SOURCE_NAME,
            "url": link,
            "published": published or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }


class ZhihuScraper(BaseScraper):
    """Scrape Zhihu for HK insurance discussions and articles."""

    SOURCE_NAME = "知乎"
    SOURCE_TYPE = "social"
    SOURCE_WEIGHT = 0.70

    def fetch_raw(self) -> list:
        items = []
        queries = ["香港保险", "港险理赔", "GN16", "港险分红"]
        for query in queries:
            try:
                url = f"https://www.zhihu.com/api/v4/search_v3?t=general&q={quote(query)}&correction=1&offset=0&limit=20"
                resp = requests.get(url, headers={
                    **HEADERS,
                    "Referer": "https://www.zhihu.com/",
                }, timeout=15)
                data = resp.json()
                results = data.get("data", [])
                for item in results:
                    items.append(item)
                logger.info("[Zhihu] Query '%s' got %d results", query, len(results))
            except Exception as e:
                logger.warning("[Zhihu] Query '%s' failed: %s", query, e)
        return items

    def parse_item(self, raw_item: dict) -> dict | None:
        obj = raw_item.get("object", raw_item)
        item_type = raw_item.get("type", "")
        title = obj.get("title", "") or obj.get("question", {}).get("title", "")
        title = clean_text(title)
        if not title or len(title) < 5:
            return None

        content = obj.get("excerpt", "") or obj.get("content", "") or ""
        summary = clean_text(content)[:500]
        url = obj.get("url", "")
        if url and not url.startswith("http"):
            url = f"https://www.zhihu.com{url}"

        return {
            "id": generate_id(title + str(obj.get("id", ""))),
            "title": title,
            "summary": summary if len(summary) > 10 else title,
            "source": self.SOURCE_NAME,
            "url": url,
            "published": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "platform_metrics": {
                "likes": obj.get("voteup_count", 0),
                "comments": obj.get("comment_count", 0),
            },
        }
