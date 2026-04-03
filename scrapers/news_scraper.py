# -*- coding: utf-8 -*-
"""
Baidu News scraper — fetch real-time news from Baidu News search.
Uses the publicly accessible Baidu News RSS / search interface.
"""

import re
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


class BaiduNewsScraper(BaseScraper):
    """Scrape Baidu News search results for HK insurance keywords."""

    SOURCE_NAME = "百度新闻"
    SOURCE_TYPE = "news"
    SOURCE_WEIGHT = 0.75

    SEARCH_QUERIES = [
        "香港保险",
        "港险 理赔",
        "港险 监管",
        "香港保险 分红实现率",
        "GN16 香港保险",
        "大湾区 保险 跨境",
        "香港 保诚 友邦 安盛",
        "水滴 港险",
    ]

    def fetch_raw(self) -> list:
        items = []
        for query in self.SEARCH_QUERIES:
            try:
                url = f"https://news.baidu.com/ns?word={quote(query)}&tn=news&from=news&cl=2&rn=20&ct=1"
                resp = requests.get(url, headers=HEADERS, timeout=15)
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")
                results = soup.select("div.result")
                if not results:
                    results = soup.select("div[class*='result']")
                for r in results:
                    items.append({"html": r, "query": query})
                logger.info("[BaiduNews] Query '%s' got %d results", query, len(results))
            except Exception as e:
                logger.warning("[BaiduNews] Query '%s' failed: %s", query, e)
        return items

    def parse_item(self, raw_item: dict) -> dict | None:
        html = raw_item["html"]

        # Title & URL
        title_tag = html.select_one("h3 a") or html.select_one("a[href]")
        if not title_tag:
            return None
        title = clean_text(title_tag.get_text())
        url = title_tag.get("href", "")

        # Summary
        summary_tag = html.select_one("div.c-summary") or html.select_one("div.c-abstract") or html.select_one("span.c-font-normal")
        summary = clean_text(summary_tag.get_text()) if summary_tag else ""

        # Source & time
        source_tag = html.select_one("span.c-color-gray") or html.select_one("p[class*='source']")
        source_text = clean_text(source_tag.get_text()) if source_tag else ""
        source_name = source_text.split("\xa0")[0] if source_text else self.SOURCE_NAME

        if not title or len(title) < 5:
            return None

        return {
            "id": generate_id(title + url),
            "title": title,
            "summary": summary if len(summary) > 20 else title,
            "source": source_name or self.SOURCE_NAME,
            "url": url,
            "published": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }


class SinaFinanceScraper(BaseScraper):
    """Scrape Sina Finance insurance section."""

    SOURCE_NAME = "新浪财经"
    SOURCE_TYPE = "news"
    SOURCE_WEIGHT = 0.85

    URLS = [
        "https://finance.sina.com.cn/money/insurance/",
        "https://finance.sina.com.cn/money/insurance/bxdt/",
    ]

    def fetch_raw(self) -> list:
        items = []
        for page_url in self.URLS:
            try:
                resp = requests.get(page_url, headers=HEADERS, timeout=15)
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")
                links = soup.select("a[href*='doc-']") + soup.select("a[href*='article']")
                for a in links:
                    href = a.get("href", "")
                    text = clean_text(a.get_text())
                    if text and len(text) > 8 and href:
                        if href.startswith("//"):
                            href = "https:" + href
                        items.append({"title": text, "url": href})
            except Exception as e:
                logger.warning("[SinaFinance] Fetch failed for %s: %s", page_url, e)
        return items

    def parse_item(self, raw_item: dict) -> dict | None:
        title = raw_item.get("title", "")
        url = raw_item.get("url", "")
        if not title or len(title) < 8:
            return None

        # Try to fetch article content for summary
        summary = title  # Fallback
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")
            # Try multiple selectors for article content
            article = (
                soup.select_one("div.article-content") or
                soup.select_one("div#artibody") or
                soup.select_one("div.article") or
                soup.select_one("section.art_pic_card")
            )
            if article:
                paragraphs = article.select("p")
                text_parts = [clean_text(p.get_text()) for p in paragraphs[:5]]
                text_parts = [t for t in text_parts if len(t) > 10]
                if text_parts:
                    summary = " ".join(text_parts)[:500]
        except Exception:
            pass  # Use title as fallback summary

        return {
            "id": generate_id(title + url),
            "title": title,
            "summary": summary,
            "url": url,
            "published": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }


class TencentNewsScraper(BaseScraper):
    """Scrape Tencent News for HK insurance topics."""

    SOURCE_NAME = "腾讯新闻"
    SOURCE_TYPE = "news"
    SOURCE_WEIGHT = 0.80

    def fetch_raw(self) -> list:
        items = []
        queries = ["香港保险", "港险 监管", "大湾区 保险"]
        for query in queries:
            try:
                url = f"https://r.inews.qq.com/gw/event/searchResult?keyword={quote(query)}&page=0&filter=news"
                resp = requests.get(url, headers=HEADERS, timeout=15)
                data = resp.json()
                news_list = data.get("data", {}).get("articleList", [])
                if not news_list:
                    news_list = data.get("data", {}).get("list", [])
                for article in news_list:
                    items.append(article)
                logger.info("[TencentNews] Query '%s' got %d results", query, len(news_list))
            except Exception as e:
                logger.warning("[TencentNews] Query '%s' failed: %s", query, e)
        return items

    def parse_item(self, raw_item: dict) -> dict | None:
        title = raw_item.get("title", "")
        url = raw_item.get("url", "") or raw_item.get("articleUrl", "")
        summary = raw_item.get("abstract", "") or raw_item.get("intro", "") or title
        published = raw_item.get("publishTime", "") or raw_item.get("publish_time", "")
        source = raw_item.get("media", "") or raw_item.get("source", "")

        if not title or len(title) < 5:
            return None

        return {
            "id": generate_id(title + url),
            "title": clean_text(title),
            "summary": clean_text(summary)[:500],
            "url": url,
            "source": source or self.SOURCE_NAME,
            "published": published or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }


class SohuFinanceScraper(BaseScraper):
    """Scrape Sohu Finance for insurance news."""

    SOURCE_NAME = "搜狐财经"
    SOURCE_TYPE = "news"
    SOURCE_WEIGHT = 0.75

    def fetch_raw(self) -> list:
        items = []
        queries = ["香港保险", "港险", "大湾区保险"]
        for query in queries:
            try:
                url = f"https://search.sohu.com/?keyword={quote(query)}&type=news&spm=smpc.csrpage.0.0"
                resp = requests.get(url, headers=HEADERS, timeout=15)
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")
                results = soup.select("div.news-item") or soup.select("div[class*='result']") or soup.select("h4 a")
                for r in results:
                    items.append({"html": r, "query": query})
            except Exception as e:
                logger.warning("[SohuFinance] Query '%s' failed: %s", query, e)
        return items

    def parse_item(self, raw_item: dict) -> dict | None:
        html = raw_item["html"]
        if html.name == "a":
            title = clean_text(html.get_text())
            url = html.get("href", "")
        else:
            title_tag = html.select_one("h4 a") or html.select_one("a")
            if not title_tag:
                return None
            title = clean_text(title_tag.get_text())
            url = title_tag.get("href", "")

        summary_tag = html.select_one("p") or html.select_one("span.content")
        summary = clean_text(summary_tag.get_text()) if summary_tag else title

        if not title or len(title) < 5:
            return None
        if url and url.startswith("//"):
            url = "https:" + url

        return {
            "id": generate_id(title + url),
            "title": title,
            "summary": summary[:500] if len(summary) > 20 else title,
            "url": url,
            "published": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }


class XueqiuScraper(BaseScraper):
    """Scrape Xueqiu (snowball) for HK insurance discussions."""

    SOURCE_NAME = "雪球"
    SOURCE_TYPE = "social"
    SOURCE_WEIGHT = 0.70

    def fetch_raw(self) -> list:
        items = []
        queries = ["香港保险", "港险", "GN16", "分红实现率"]
        for query in queries:
            try:
                url = f"https://xueqiu.com/query/v1/search/web/search.json?q={quote(query)}&type=post&count=20"
                resp = requests.get(url, headers={**HEADERS, "Origin": "https://xueqiu.com"}, timeout=15)
                data = resp.json()
                posts = data.get("list", [])
                for post in posts:
                    items.append(post)
            except Exception as e:
                logger.warning("[Xueqiu] Query '%s' failed: %s", query, e)
        return items

    def parse_item(self, raw_item: dict) -> dict | None:
        title = raw_item.get("title", "") or raw_item.get("description", "")
        title = clean_text(title)
        summary = clean_text(raw_item.get("description", "") or title)
        url = raw_item.get("target", "") or raw_item.get("url", "")
        if url and not url.startswith("http"):
            url = f"https://xueqiu.com{url}"

        if not title or len(title) < 5:
            return None

        return {
            "id": generate_id(title + url),
            "title": title[:200],
            "summary": summary[:500],
            "url": url,
            "published": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "platform_metrics": {
                "likes": raw_item.get("like_count", 0),
                "comments": raw_item.get("reply_count", 0),
                "shares": raw_item.get("retweet_count", 0),
            },
        }
