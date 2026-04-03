# -*- coding: utf-8 -*-
"""
Social media scrapers — Weibo, Xiaohongshu (Little Red Book).
These use publicly accessible web search / API endpoints.
"""

import re
import json
import logging
import requests
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


class WeiboScraper(BaseScraper):
    """Scrape Weibo search for HK insurance discussions.
    Uses the mobile web search which is publicly accessible.
    """

    SOURCE_NAME = "微博"
    SOURCE_TYPE = "social"
    SOURCE_WEIGHT = 0.70

    SEARCH_QUERIES = [
        "香港保险",
        "港险理赔",
        "港险避坑",
        "香港保险分红",
        "GN16保险",
    ]

    def fetch_raw(self) -> list:
        items = []
        for query in self.SEARCH_QUERIES:
            try:
                # Weibo mobile search is more accessible
                url = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{quote(query)}&page_type=searchall&page=1"
                resp = requests.get(url, headers={
                    **HEADERS,
                    "Referer": "https://m.weibo.cn/",
                    "X-Requested-With": "XMLHttpRequest",
                }, timeout=15)
                data = resp.json()
                cards = data.get("data", {}).get("cards", [])
                for card in cards:
                    if card.get("card_type") == 9:
                        items.append(card.get("mblog", {}))
                    elif card.get("card_group"):
                        for sub in card["card_group"]:
                            if sub.get("card_type") == 9:
                                items.append(sub.get("mblog", {}))
                logger.info("[Weibo] Query '%s' got %d items", query, len(cards))
            except Exception as e:
                logger.warning("[Weibo] Query '%s' failed: %s", query, e)
        return items

    def parse_item(self, raw_item: dict) -> dict | None:
        text_raw = raw_item.get("text", "")
        text = clean_text(text_raw)
        if not text or len(text) < 10:
            return None

        # Extract a title (first sentence or first 60 chars)
        first_sentence = re.split(r"[。！？\n]", text)[0]
        title = first_sentence[:80] if first_sentence else text[:80]

        mid = raw_item.get("mid", "") or raw_item.get("id", "")
        user = raw_item.get("user", {})
        username = user.get("screen_name", "微博用户")
        followers = user.get("followers_count", 0)
        url = f"https://m.weibo.cn/detail/{mid}" if mid else ""

        # Determine author influence
        if followers > 1000000:
            influence = "大V"
        elif followers > 100000:
            influence = "KOL"
        elif followers > 10000:
            influence = "活跃用户"
        else:
            influence = "普通用户"

        return {
            "id": generate_id(str(mid) + text[:50]),
            "title": title,
            "summary": text[:500],
            "source": f"微博 @{username}",
            "url": url,
            "published": raw_item.get("created_at", datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
            "content_type": "text",
            "author_influence": influence,
            "platform_metrics": {
                "likes": raw_item.get("attitudes_count", 0),
                "comments": raw_item.get("comments_count", 0),
                "shares": raw_item.get("reposts_count", 0),
            },
        }


class XiaohongshuScraper(BaseScraper):
    """Scrape Xiaohongshu (Little Red Book) for HK insurance content.
    Uses the web search which returns some public results.
    """

    SOURCE_NAME = "小红书"
    SOURCE_TYPE = "social"
    SOURCE_WEIGHT = 0.65

    SEARCH_QUERIES = [
        "香港保险攻略",
        "港险避坑",
        "香港保险理赔",
        "港险分红实现率",
        "香港保险经验",
        "港险怎么买",
    ]

    def fetch_raw(self) -> list:
        items = []
        for query in self.SEARCH_QUERIES:
            try:
                # Xiaohongshu web search
                url = f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}&type=51"
                resp = requests.get(url, headers={
                    **HEADERS,
                    "Referer": "https://www.xiaohongshu.com/",
                }, timeout=15)
                # Try to extract JSON data from the page
                soup = BeautifulSoup(resp.text, "lxml")
                # Look for embedded data
                scripts = soup.select("script")
                for script in scripts:
                    text = script.get_text()
                    if "window.__INITIAL_STATE__" in text or "window.__INITIAL_SSR_STATE__" in text:
                        json_match = re.search(r"=\s*({.+})\s*;?\s*$", text, re.DOTALL)
                        if json_match:
                            try:
                                data = json.loads(json_match.group(1).replace("undefined", "null"))
                                notes = self._extract_notes(data)
                                items.extend(notes)
                            except json.JSONDecodeError:
                                pass

                # Fallback: parse visible note cards from HTML
                if not items:
                    note_cards = soup.select("section.note-item") or soup.select("div[class*='note']") or soup.select("a[href*='/explore/']")
                    for card in note_cards:
                        title_el = card.select_one("span") or card.select_one("p")
                        if title_el:
                            items.append({
                                "title": clean_text(title_el.get_text()),
                                "url": card.get("href", ""),
                                "query": query,
                            })

                logger.info("[Xiaohongshu] Query '%s' got %d items", query, len(items))
            except Exception as e:
                logger.warning("[Xiaohongshu] Query '%s' failed: %s", query, e)
        return items

    def _extract_notes(self, data: dict) -> list:
        """Recursively search for note data in the SSR state."""
        notes = []
        if isinstance(data, dict):
            if "noteId" in data or "note_id" in data:
                notes.append(data)
            for v in data.values():
                notes.extend(self._extract_notes(v))
        elif isinstance(data, list):
            for item in data:
                notes.extend(self._extract_notes(item))
        return notes

    def parse_item(self, raw_item: dict) -> dict | None:
        title = raw_item.get("title", "") or raw_item.get("displayTitle", "")
        title = clean_text(title)
        if not title or len(title) < 5:
            return None

        note_id = raw_item.get("noteId", "") or raw_item.get("note_id", "") or raw_item.get("id", "")
        desc = raw_item.get("desc", "") or raw_item.get("description", "") or ""
        summary = clean_text(desc)[:500] if desc else title

        url = raw_item.get("url", "")
        if not url and note_id:
            url = f"https://www.xiaohongshu.com/explore/{note_id}"
        elif url and url.startswith("/"):
            url = f"https://www.xiaohongshu.com{url}"

        likes = raw_item.get("likes", 0) or raw_item.get("likedCount", 0) or 0
        content_type = "video" if raw_item.get("type") == "video" else "note"

        return {
            "id": generate_id(title + str(note_id)),
            "title": title[:200],
            "summary": summary if len(summary) > 10 else title,
            "source": self.SOURCE_NAME,
            "url": url,
            "published": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "content_type": content_type,
            "author_influence": "UGC",
            "platform_metrics": {
                "likes": likes,
                "comments": raw_item.get("comments", 0) or raw_item.get("commentCount", 0),
                "shares": raw_item.get("shareCount", 0),
                "collects": raw_item.get("collectedCount", 0),
            },
        }


class WechatArticleScraper(BaseScraper):
    """Scrape WeChat public articles via Sogou WeChat search.
    This is the most accessible way to find WeChat public account articles.
    """

    SOURCE_NAME = "微信公众号"
    SOURCE_TYPE = "social"
    SOURCE_WEIGHT = 0.75

    SEARCH_QUERIES = [
        "香港保险",
        "港险 GN16",
        "港险理赔经验",
        "香港保险分红",
        "大湾区保险",
    ]

    def fetch_raw(self) -> list:
        items = []
        for query in self.SEARCH_QUERIES:
            try:
                url = f"https://weixin.sogou.com/weixin?type=2&query={quote(query)}&ie=utf8"
                resp = requests.get(url, headers={
                    **HEADERS,
                    "Referer": "https://weixin.sogou.com/",
                }, timeout=15)
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")
                results = soup.select("div.txt-box") or soup.select("ul.news-list li")
                for r in results:
                    items.append({"html": r, "query": query})
                logger.info("[WechatArticle] Query '%s' got %d results", query, len(results))
            except Exception as e:
                logger.warning("[WechatArticle] Query '%s' failed: %s", query, e)
        return items

    def parse_item(self, raw_item: dict) -> dict | None:
        html = raw_item["html"]
        title_tag = html.select_one("h3 a") or html.select_one("a")
        if not title_tag:
            return None
        title = clean_text(title_tag.get_text())
        url = title_tag.get("href", "")
        if url and url.startswith("/"):
            url = "https://weixin.sogou.com" + url

        summary_tag = html.select_one("p.txt-info") or html.select_one("p")
        summary = clean_text(summary_tag.get_text()) if summary_tag else title

        account_tag = html.select_one("a.account") or html.select_one("span.s-p")
        account = clean_text(account_tag.get_text()) if account_tag else "公众号"

        if not title or len(title) < 5:
            return None

        return {
            "id": generate_id(title + url),
            "title": title,
            "summary": summary[:500] if len(summary) > 20 else title,
            "source": f"公众号:{account}" if account != "公众号" else self.SOURCE_NAME,
            "url": url,
            "published": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "content_type": "article",
        }
