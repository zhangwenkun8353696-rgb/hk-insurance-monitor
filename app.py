# -*- coding: utf-8 -*-
"""
HK Insurance Monitor — Main Application
Full-featured Flask backend with real data scraping, analysis engine,
target company strategy, and comprehensive APIs.
"""

import os
import re
import json
import logging
import threading
from datetime import datetime, timedelta
from collections import Counter

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, upsert_news, get_news_list, get_dashboard_stats, set_target_company, get_target_company, log_scrape
from scrapers.news_scraper import BaiduNewsScraper, SinaFinanceScraper, TencentNewsScraper, SohuFinanceScraper, XueqiuScraper
from scrapers.social_scraper import WeiboScraper, XiaohongshuScraper, WechatArticleScraper
from scrapers.official_scraper import HKIAScraper, GoogleNewsScraper, ZhihuScraper

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Flask App
# ──────────────────────────────────────────────
app = Flask(__name__, static_folder="static")
CORS(app)

# ──────────────────────────────────────────────
# Companies Registry (HK + Mainland)
# ──────────────────────────────────────────────
COMPANIES = {
    # === Hong Kong Licensed Insurers ===
    "prudential": {
        "id": "prudential", "name": "保诚", "name_en": "Prudential",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["保诚", "Prudential", "英国保诚"],
        "description": "英国保诚集团旗下香港寿险公司，市场份额领先",
    },
    "aia": {
        "id": "aia", "name": "友邦", "name_en": "AIA",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["友邦", "AIA", "友邦保险"],
        "description": "亚太地区最大独立上市寿险集团",
    },
    "axa": {
        "id": "axa", "name": "安盛", "name_en": "AXA",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["安盛", "AXA", "AXA安盛"],
        "description": "法国安盛集团香港子公司",
    },
    "manulife": {
        "id": "manulife", "name": "宏利", "name_en": "Manulife",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["宏利", "Manulife", "宏利保险"],
        "description": "加拿大宏利金融集团香港子公司",
    },
    "sunlife": {
        "id": "sunlife", "name": "永明", "name_en": "Sun Life",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["永明", "Sun Life", "永明金融"],
        "description": "加拿大永明金融集团香港子公司",
    },
    "ftlife": {
        "id": "ftlife", "name": "富通", "name_en": "FTLife",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["富通", "FTLife", "富通保险"],
        "description": "新世界集团旗下寿险公司",
    },
    "china_life_overseas": {
        "id": "china_life_overseas", "name": "中国人寿(海外)", "name_en": "China Life Overseas",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["中国人寿海外", "中国人寿(海外)", "China Life Overseas"],
        "description": "中国人寿集团海外子公司",
    },
    "boclife": {
        "id": "boclife", "name": "中银人寿", "name_en": "BOC Life",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["中银人寿", "BOC Life", "中银保险"],
        "description": "中国银行集团旗下香港寿险公司",
    },
    "zurich": {
        "id": "zurich", "name": "苏黎世", "name_en": "Zurich",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["苏黎世", "Zurich", "苏黎世保险"],
        "description": "瑞士苏黎世保险集团香港分支",
    },
    "generali": {
        "id": "generali", "name": "忠意", "name_en": "Generali",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["忠意", "Generali", "忠意保险"],
        "description": "意大利忠利集团香港子公司",
    },
    "chubb": {
        "id": "chubb", "name": "安达", "name_en": "Chubb",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["安达", "Chubb", "安达保险"],
        "description": "全球最大上市财险集团香港分支",
    },
    "taiping": {
        "id": "taiping", "name": "太平", "name_en": "China Taiping",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["太平", "China Taiping", "太平人寿", "中国太平"],
        "description": "中国太平保险集团香港子公司",
    },
    "yf_life": {
        "id": "yf_life", "name": "万通", "name_en": "YF Life",
        "region": "hk", "type": "hk_licensed",
        "keywords": ["万通", "YF Life", "万通保险"],
        "description": "万通保险国际有限公司",
    },

    # === Mainland Companies Doing HK Insurance Business ===
    "shuidrop": {
        "id": "shuidrop", "name": "水滴", "name_en": "Waterdrop",
        "region": "mainland", "type": "mainland_broker",
        "keywords": ["水滴", "水滴保", "水滴公司", "Waterdrop", "水滴筹"],
        "description": "互联网保险科技平台，布局跨境保险业务",
    },
    "snailinsure": {
        "id": "snailinsure", "name": "蜗牛保", "name_en": "Snail Insurance",
        "region": "mainland", "type": "mainland_broker",
        "keywords": ["蜗牛保", "蜗牛保险", "蜗牛保险经纪"],
        "description": "互联网保险经纪平台，提供港险咨询服务",
    },
    "huize": {
        "id": "huize", "name": "慧择", "name_en": "Huize",
        "region": "mainland", "type": "mainland_broker",
        "keywords": ["慧择", "慧择保险", "Huize"],
        "description": "纳斯达克上市互联网保险平台",
    },
    "elephant": {
        "id": "elephant", "name": "大象保险", "name_en": "Elephant Insurance",
        "region": "mainland", "type": "mainland_broker",
        "keywords": ["大象保险"],
        "description": "AI驱动的互联网保险平台",
    },
    "xiaoyusan": {
        "id": "xiaoyusan", "name": "小雨伞", "name_en": "Xiaoyusan",
        "region": "mainland", "type": "mainland_broker",
        "keywords": ["小雨伞", "小雨伞保险"],
        "description": "互联网保险服务平台",
    },
    "ant_insurance": {
        "id": "ant_insurance", "name": "蚂蚁保", "name_en": "Ant Insurance",
        "region": "mainland", "type": "mainland_platform",
        "keywords": ["蚂蚁保", "蚂蚁保险", "支付宝保险"],
        "description": "蚂蚁集团旗下保险服务平台",
    },
    "tencent_weibao": {
        "id": "tencent_weibao", "name": "微保", "name_en": "WeSure",
        "region": "mainland", "type": "mainland_platform",
        "keywords": ["微保", "WeSure", "腾讯微保"],
        "description": "腾讯旗下互联网保险平台",
    },
}

# ──────────────────────────────────────────────
# Topic / Category Definitions
# ──────────────────────────────────────────────
TOPICS = {
    "regulation": {"name": "监管政策", "keywords": ["监管", "保监局", "GN16", "指引", "牌照", "合规", "RBC", "偿付能力"]},
    "claims": {"name": "理赔纠纷", "keywords": ["理赔", "拒赔", "投诉", "纠纷", "维权", "诉讼"]},
    "dividend": {"name": "分红实现率", "keywords": ["分红实现率", "分红", "红利", "回报率", "收益率", "IRR"]},
    "cross_border": {"name": "跨境业务", "keywords": ["跨境", "大湾区", "内地客", "CRS", "两地互通", "通关"]},
    "product": {"name": "产品动态", "keywords": ["新产品", "升级", "停售", "重疾险", "储蓄险", "万用寿险"]},
    "market": {"name": "市场趋势", "keywords": ["市场份额", "保费收入", "季报", "年报", "业绩", "增长"]},
    "insurtech": {"name": "保险科技", "keywords": ["InsurTech", "保险科技", "数字化", "AI", "智能核保", "区块链"]},
    "reputation": {"name": "品牌声誉", "keywords": ["口碑", "评价", "推荐", "避坑", "经验分享", "测评"]},
}

# ──────────────────────────────────────────────
# Analysis Engine
# ──────────────────────────────────────────────
class AnalysisEngine:
    """Analyze news items: sentiment, risk, topics, companies, key facts."""

    POSITIVE_WORDS = [
        "增长", "上涨", "利好", "突破", "创新", "领先", "优质", "提升",
        "受益", "回报", "稳健", "丰厚", "好评", "推荐", "获批", "扩展",
        "合作", "战略", "升级", "满意", "高效", "领跑", "超额", "分红提升",
    ]
    NEGATIVE_WORDS = [
        "下跌", "亏损", "投诉", "拒赔", "罚款", "违规", "风险", "下降",
        "纠纷", "诈骗", "误导", "暴雷", "踩坑", "避坑", "维权", "处罚",
        "警告", "停售", "退保", "欺诈", "黑幕", "坑人", "虚假", "违法",
    ]

    def analyze(self, news_item: dict) -> dict:
        """Run full analysis pipeline on a single news item."""
        text = (news_item.get("title", "") + " " + news_item.get("summary", "")).lower()

        # Sentiment analysis
        sentiment, score = self._analyze_sentiment(text)
        news_item["sentiment"] = sentiment
        news_item["sentiment_score"] = score

        # Risk level
        news_item["risk_level"] = self._assess_risk(text, sentiment, score, news_item)

        # Topic classification
        news_item["topics"] = self._classify_topics(text)

        # Company identification
        news_item["companies"] = self._identify_companies(text)

        # Key facts extraction
        news_item["key_facts"] = self._extract_key_facts(text)
        news_item["key_numbers"] = self._extract_numbers(text)

        # Impact assessment
        news_item["impact_assessment"] = self._assess_impact(news_item)

        return news_item

    def _analyze_sentiment(self, text: str) -> tuple:
        pos_count = sum(1 for w in self.POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in text)
        total = pos_count + neg_count
        if total == 0:
            return "neutral", 0.5
        score = pos_count / total
        if score > 0.6:
            return "positive", min(0.95, 0.5 + score * 0.4)
        elif score < 0.4:
            return "negative", max(0.05, 0.5 - (1 - score) * 0.4)
        return "neutral", 0.5

    def _assess_risk(self, text: str, sentiment: str, score: float, item: dict) -> str:
        risk_score = 0
        high_risk_words = ["罚款", "违规", "诈骗", "暴雷", "处罚", "违法", "停售", "监管处分"]
        medium_risk_words = ["投诉", "拒赔", "纠纷", "维权", "退保", "误导", "避坑"]

        for w in high_risk_words:
            if w in text:
                risk_score += 3
        for w in medium_risk_words:
            if w in text:
                risk_score += 1

        if sentiment == "negative":
            risk_score += 2

        # Social media amplification
        metrics = item.get("platform_metrics", {})
        engagement = (metrics.get("likes", 0) + metrics.get("comments", 0) * 2 + metrics.get("shares", 0) * 3)
        if engagement > 10000:
            risk_score += 2
        elif engagement > 1000:
            risk_score += 1

        if item.get("author_influence") in ("大V", "KOL"):
            risk_score += 1

        if risk_score >= 5:
            return "high"
        elif risk_score >= 2:
            return "medium"
        return "low"

    def _classify_topics(self, text: str) -> list:
        matched = []
        for topic_id, topic in TOPICS.items():
            if any(kw.lower() in text for kw in topic["keywords"]):
                matched.append(topic_id)
        return matched or ["general"]

    def _identify_companies(self, text: str) -> list:
        matched = []
        for cid, company in COMPANIES.items():
            if any(kw.lower() in text for kw in company["keywords"]):
                matched.append(cid)
        return matched

    def _extract_key_facts(self, text: str) -> list:
        facts = []
        patterns = [
            (r"(\d+\.?\d*%)", "percentage"),
            (r"([\d,]+\s*(?:亿|万|百万|千万))", "amount"),
            (r"(第[一二三四五六七八九十\d]+(?:季度|季|年|月|名|位))", "ranking"),
            (r"(同比(?:增长|下降|上涨|下跌)\s*\d+\.?\d*%)", "yoy_change"),
        ]
        for pattern, fact_type in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                facts.append({"type": fact_type, "value": m})
        return facts[:10]

    def _extract_numbers(self, text: str) -> list:
        numbers = re.findall(r"(\d+\.?\d*)\s*(亿|万|百万|千万|%|元|港元|美元)", text)
        return [{"value": n[0], "unit": n[1]} for n in numbers[:10]]

    def _assess_impact(self, item: dict) -> str:
        companies = item.get("companies", [])
        risk = item.get("risk_level", "low")
        sentiment = item.get("sentiment", "neutral")
        topics = item.get("topics", [])

        parts = []
        if companies:
            names = [COMPANIES[c]["name"] for c in companies if c in COMPANIES]
            parts.append(f"涉及公司：{'、'.join(names)}")

        if risk == "high":
            parts.append("⚠️ 高风险事件，需重点关注")
        elif risk == "medium":
            parts.append("⚡ 中等风险，建议持续追踪")

        topic_names = [TOPICS[t]["name"] for t in topics if t in TOPICS]
        if topic_names:
            parts.append(f"相关领域：{'、'.join(topic_names)}")

        if sentiment == "negative" and "regulation" in topics:
            parts.append("监管负面消息可能影响行业信心")
        elif sentiment == "positive" and "cross_border" in topics:
            parts.append("跨境利好可能带来业务增长机会")

        return " | ".join(parts) if parts else "一般性信息"


# ──────────────────────────────────────────────
# Strategy Engine
# ──────────────────────────────────────────────
class StrategyEngine:
    """Generate strategic recommendations based on news and target company context."""

    def generate_strategies(self, news_items: list, target_company_id: str = None) -> dict:
        """Generate strategies based on recent news landscape."""
        if not news_items:
            return {"strategies": [], "summary": "暂无足够数据生成策略建议"}

        target = COMPANIES.get(target_company_id) if target_company_id else None

        # Aggregate signals
        sentiments = Counter(item.get("sentiment", "neutral") for item in news_items)
        risks = Counter(item.get("risk_level", "low") for item in news_items)
        all_topics = []
        all_companies = []
        for item in news_items:
            all_topics.extend(item.get("topics", []))
            all_companies.extend(item.get("companies", []))
        topic_counts = Counter(all_topics)
        company_counts = Counter(all_companies)

        strategies = []

        # P0 — Immediate action needed
        high_risk_news = [n for n in news_items if n.get("risk_level") == "high"]
        if high_risk_news:
            affected = set()
            for n in high_risk_news:
                affected.update(n.get("companies", []))
            company_names = [COMPANIES[c]["name"] for c in affected if c in COMPANIES]
            strategies.append({
                "priority": "P0",
                "type": "risk_alert",
                "title": "高风险舆情预警",
                "content": f"发现 {len(high_risk_news)} 条高风险新闻，涉及：{'、'.join(company_names) or '行业整体'}。建议立即启动舆情应对预案，密切监控后续发展。",
                "actions": [
                    "启动舆情应对小组",
                    "准备官方回应口径",
                    "监控社交媒体传播态势",
                    "评估对业务的直接影响",
                ],
            })

        # P1 — Strategic opportunities / threats
        if topic_counts.get("cross_border", 0) > 2:
            strategies.append({
                "priority": "P1",
                "type": "opportunity",
                "title": "跨境业务机遇",
                "content": f"近期跨境/大湾区相关新闻共 {topic_counts['cross_border']} 条，信号密集。{'建议' + target['name'] + '加大跨境业务投入' if target else '跨境保险市场活跃度上升'}。",
                "actions": [
                    "评估大湾区保险通新政策影响",
                    "优化跨境理赔流程",
                    "加强与大陆渠道合作",
                ],
            })

        if topic_counts.get("regulation", 0) > 3:
            strategies.append({
                "priority": "P1",
                "type": "compliance",
                "title": "监管动态密集期",
                "content": f"监管相关新闻达 {topic_counts['regulation']} 条。{'建议' + target['name'] + '排查合规风险' if target else '行业合规压力增大'}。",
                "actions": [
                    "审查产品合规性",
                    "更新销售话术和披露文件",
                    "关注GN16执行细则变化",
                ],
            })

        if topic_counts.get("dividend", 0) > 2:
            strategies.append({
                "priority": "P1",
                "type": "product",
                "title": "分红实现率关注度上升",
                "content": f"分红相关讨论 {topic_counts['dividend']} 条。消费者对分红透明度需求增强。",
                "actions": [
                    "提前准备分红实现率报告",
                    "优化分红披露方式",
                    "对比竞品分红表现",
                ],
            })

        # P2 — Market intelligence
        if sentiments.get("negative", 0) > sentiments.get("positive", 0):
            strategies.append({
                "priority": "P2",
                "type": "market_insight",
                "title": "行业舆情偏负面",
                "content": f"负面新闻({sentiments.get('negative', 0)}条) > 正面({sentiments.get('positive', 0)}条)。整体市场信心偏弱。",
                "actions": [
                    "加强正面品牌传播",
                    "收集客户满意案例",
                    "准备舆情恢复计划",
                ],
            })

        # Target company specific
        if target and target_company_id in company_counts:
            mention_count = company_counts[target_company_id]
            target_news = [n for n in news_items if target_company_id in n.get("companies", [])]
            target_sentiments = Counter(n.get("sentiment", "neutral") for n in target_news)

            strategies.append({
                "priority": "P1",
                "type": "target_focus",
                "title": f"{target['name']}舆情分析",
                "content": (
                    f"目标公司 {target['name']} 近期被提及 {mention_count} 次。"
                    f"正面 {target_sentiments.get('positive', 0)} / "
                    f"中性 {target_sentiments.get('neutral', 0)} / "
                    f"负面 {target_sentiments.get('negative', 0)}。"
                ),
                "actions": self._target_actions(target, target_sentiments, target_news),
            })

        # Competitor analysis
        if target:
            competitors = [c for c in company_counts if c != target_company_id and c in COMPANIES][:5]
            if competitors:
                comp_info = []
                for comp_id in competitors:
                    comp_news = [n for n in news_items if comp_id in n.get("companies", [])]
                    comp_sent = Counter(n.get("sentiment") for n in comp_news)
                    comp_info.append(
                        f"{COMPANIES[comp_id]['name']}(提及{company_counts[comp_id]}次, "
                        f"+{comp_sent.get('positive',0)}/-{comp_sent.get('negative',0)})"
                    )
                strategies.append({
                    "priority": "P2",
                    "type": "competitor",
                    "title": "竞品动态概览",
                    "content": "主要竞品近期表现：" + "；".join(comp_info),
                    "actions": [
                        "对比竞品产品优劣势",
                        "关注竞品负面事件的借鉴意义",
                        "评估市场份额变化趋势",
                    ],
                })

        # Summary
        summary = self._generate_summary(sentiments, risks, topic_counts, target)

        return {
            "strategies": sorted(strategies, key=lambda s: {"P0": 0, "P1": 1, "P2": 2}.get(s["priority"], 3)),
            "summary": summary,
            "signals": {
                "sentiment": dict(sentiments),
                "risk": dict(risks),
                "hot_topics": dict(topic_counts.most_common(5)),
                "active_companies": dict(company_counts.most_common(10)),
            },
        }

    def _target_actions(self, target: dict, sentiments: Counter, news: list) -> list:
        actions = []
        if sentiments.get("negative", 0) > 0:
            actions.append(f"关注{target['name']}负面舆情，及时应对")
        if sentiments.get("positive", 0) > sentiments.get("negative", 0):
            actions.append("积极传播正面消息，扩大品牌影响")
        actions.append(f"追踪{target['name']}核心业务指标变化")
        actions.append("评估舆情对客户决策的影响")
        return actions

    def _generate_summary(self, sentiments, risks, topics, target) -> str:
        total = sum(sentiments.values())
        neg_pct = sentiments.get("negative", 0) / max(total, 1) * 100
        parts = [f"监控 {total} 条新闻"]
        if neg_pct > 30:
            parts.append(f"负面情绪占比 {neg_pct:.0f}%，偏高")
        else:
            parts.append(f"舆情整体{'偏正面' if sentiments.get('positive', 0) > sentiments.get('negative', 0) else '平稳'}")
        hot = topics.most_common(2)
        if hot:
            parts.append(f"热点话题：{'、'.join(TOPICS.get(t[0], {}).get('name', t[0]) for t in hot)}")
        if target:
            parts.append(f"目标公司：{target['name']}")
        return "。".join(parts) + "。"


# ──────────────────────────────────────────────
# Scraping Orchestrator
# ──────────────────────────────────────────────
analysis_engine = AnalysisEngine()
strategy_engine = StrategyEngine()

ALL_SCRAPERS = [
    BaiduNewsScraper(),
    SinaFinanceScraper(),
    TencentNewsScraper(),
    SohuFinanceScraper(),
    XueqiuScraper(),
    WeiboScraper(),
    XiaohongshuScraper(),
    WechatArticleScraper(),
    HKIAScraper(),
    GoogleNewsScraper(),
    ZhihuScraper(),
]

_scrape_status = {"running": False, "last_run": None, "results": {}}


def run_scrape_all():
    """Run all scrapers, analyze results, save to DB."""
    global _scrape_status
    if _scrape_status["running"]:
        logger.info("Scrape already running, skipping.")
        return
    _scrape_status["running"] = True
    _scrape_status["results"] = {}
    logger.info("=== Starting full scrape cycle ===")

    total_saved = 0
    for scraper in ALL_SCRAPERS:
        source_name = scraper.SOURCE_NAME
        try:
            items = scraper.get_news()
            saved = 0
            for item in items:
                try:
                    analyzed = analysis_engine.analyze(item)
                    upsert_news(analyzed)
                    saved += 1
                except Exception as e:
                    logger.warning("Failed to save item from %s: %s", source_name, e)
            log_scrape(source_name, len(items), saved)
            _scrape_status["results"][source_name] = {"fetched": len(items), "saved": saved}
            total_saved += saved
            logger.info("[%s] Done: %d fetched, %d saved", source_name, len(items), saved)
        except Exception as e:
            logger.error("[%s] Scraper failed: %s", source_name, e)
            log_scrape(source_name, 0, 0, str(e))
            _scrape_status["results"][source_name] = {"fetched": 0, "saved": 0, "error": str(e)}

    _scrape_status["running"] = False
    _scrape_status["last_run"] = datetime.now().isoformat()
    logger.info("=== Scrape complete: %d items saved ===", total_saved)


def run_scrape_async():
    """Run scraping in a background thread."""
    t = threading.Thread(target=run_scrape_all, daemon=True)
    t.start()


# ──────────────────────────────────────────────
# API Routes
# ──────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/news")
def api_news():
    """Paginated, filtered news list."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sentiment = request.args.get("sentiment")
    company = request.args.get("company")
    topic = request.args.get("topic")
    risk = request.args.get("risk")
    source_type = request.args.get("source_type")
    search = request.args.get("search")

    items, total = get_news_list(
        page=page, per_page=per_page,
        sentiment=sentiment, company=company, topic=topic,
        risk=risk, source_type=source_type, search=search,
    )
    return jsonify({
        "news": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })


@app.route("/api/dashboard")
def api_dashboard():
    """Dashboard statistics."""
    stats = get_dashboard_stats()
    stats["companies"] = COMPANIES
    stats["topics"] = {k: v["name"] for k, v in TOPICS.items()}
    stats["target_company"] = get_target_company()
    return jsonify(stats)


@app.route("/api/companies")
def api_companies():
    """List all monitored companies."""
    region = request.args.get("region")  # hk, mainland, or all
    result = {}
    for cid, company in COMPANIES.items():
        if not region or region == "all" or company["region"] == region:
            result[cid] = company
    return jsonify(result)


@app.route("/api/target", methods=["GET", "POST"])
def api_target():
    """Get or set target company."""
    if request.method == "POST":
        data = request.get_json(force=True)
        company_id = data.get("company_id", "")
        if company_id not in COMPANIES:
            return jsonify({"error": "Invalid company_id"}), 400
        set_target_company(company_id)
        return jsonify({"ok": True, "target": company_id, "company": COMPANIES[company_id]})
    else:
        target_id = get_target_company()
        return jsonify({
            "target": target_id,
            "company": COMPANIES.get(target_id) if target_id else None,
        })


@app.route("/api/strategies")
def api_strategies():
    """Generate strategies based on current news and target company."""
    target_id = get_target_company()
    # Get recent news for analysis
    items, _ = get_news_list(page=1, per_page=200)
    result = strategy_engine.generate_strategies(items, target_id)
    # Attach related news map for drill-down
    result["related_news_map"] = _build_strategy_news_map(result.get("strategies", []), items, target_id)
    return jsonify(result)


def _build_strategy_news_map(strategies, news_items, target_id):
    """Build a map of strategy type -> related news items for drill-down."""
    result = {}
    for s in strategies:
        stype = s.get("type", "")
        related = []
        if stype == "risk_alert":
            related = [n for n in news_items if n.get("risk_level") == "high"]
        elif stype == "target_focus" and target_id:
            related = [n for n in news_items if target_id in n.get("companies", [])]
        elif stype == "competitor":
            # All news mentioning non-target companies
            related = [n for n in news_items if n.get("companies") and (not target_id or target_id not in n.get("companies", []))][:20]
        elif stype == "opportunity":
            related = [n for n in news_items if "cross_border" in n.get("topics", [])]
        elif stype == "compliance":
            related = [n for n in news_items if "regulation" in n.get("topics", [])]
        elif stype == "product":
            related = [n for n in news_items if "dividend" in n.get("topics", [])]
        elif stype == "market_insight":
            related = [n for n in news_items if n.get("sentiment") == "negative"]
        else:
            related = []
        # Only keep essential fields
        result[stype] = [{
            "id": n.get("id"),
            "title": n.get("title", ""),
            "source": n.get("source", ""),
            "url": n.get("url", ""),
            "sentiment": n.get("sentiment", ""),
            "risk_level": n.get("risk_level", ""),
            "published": n.get("published", ""),
            "summary": (n.get("summary", "") or "")[:200],
            "companies": n.get("companies", []),
        } for n in related[:10]]
    return result


@app.route("/api/industry_analysis")
def api_industry_analysis():
    """Industry-level sentiment and risk analysis for dashboard."""
    items, total = get_news_list(page=1, per_page=500)
    sentiments = Counter(n.get("sentiment", "neutral") for n in items)
    risks = Counter(n.get("risk_level", "low") for n in items)

    # Topic breakdown with sentiment
    topic_analysis = {}
    for n in items:
        for t in n.get("topics", []):
            if t not in topic_analysis:
                topic_analysis[t] = {"total": 0, "positive": 0, "neutral": 0, "negative": 0, "high_risk": 0}
            topic_analysis[t]["total"] += 1
            topic_analysis[t][n.get("sentiment", "neutral")] += 1
            if n.get("risk_level") == "high":
                topic_analysis[t]["high_risk"] += 1

    # Risk news (high + medium, limited)
    risk_news = [{
        "id": n.get("id"), "title": n.get("title"), "source": n.get("source"),
        "url": n.get("url"), "sentiment": n.get("sentiment"),
        "risk_level": n.get("risk_level"), "published": n.get("published"),
        "summary": (n.get("summary", "") or "")[:200],
        "companies": n.get("companies", []),
        "topics": n.get("topics", []),
    } for n in items if n.get("risk_level") in ("high", "medium")][:30]

    return jsonify({
        "total": total,
        "sentiment": dict(sentiments),
        "risk": dict(risks),
        "topic_analysis": topic_analysis,
        "risk_news": risk_news,
    })


@app.route("/api/company_analysis")
def api_company_analysis():
    """Target-company-level analysis for dashboard drill-down."""
    target_id = request.args.get("company_id") or get_target_company()
    if not target_id or target_id not in COMPANIES:
        return jsonify({"error": "No target company set", "news": [], "stats": {}}), 200

    items, _ = get_news_list(page=1, per_page=500, company=target_id)
    company = COMPANIES[target_id]

    sentiments = Counter(n.get("sentiment", "neutral") for n in items)
    risks = Counter(n.get("risk_level", "low") for n in items)
    topics = Counter()
    for n in items:
        for t in n.get("topics", []):
            topics[t] += 1

    # All company news with urls for drill-down
    news_list = [{
        "id": n.get("id"), "title": n.get("title"), "source": n.get("source"),
        "url": n.get("url"), "sentiment": n.get("sentiment"),
        "risk_level": n.get("risk_level"), "published": n.get("published"),
        "summary": (n.get("summary", "") or "")[:200],
        "topics": n.get("topics", []),
    } for n in items]

    return jsonify({
        "company": company,
        "company_id": target_id,
        "total": len(items),
        "sentiment": dict(sentiments),
        "risk": dict(risks),
        "topics": dict(topics.most_common(10)),
        "news": news_list[:50],
    })


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Trigger a manual scrape."""
    if _scrape_status["running"]:
        return jsonify({"status": "already_running", "message": "采集正在进行中..."})
    run_scrape_async()
    return jsonify({"status": "started", "message": "采集已启动，请稍候..."})


@app.route("/api/scrape/status")
def api_scrape_status():
    """Get scrape status."""
    return jsonify(_scrape_status)


@app.route("/api/topics")
def api_topics():
    """List all topics."""
    return jsonify({k: v["name"] for k, v in TOPICS.items()})


# ──────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────
def create_app():
    """Initialize and return the Flask app."""
    init_db()
    logger.info("Database initialized.")

    # Schedule scraping every 2 hours
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scrape_all, "interval", hours=2, id="scrape_all", max_instances=1)
    scheduler.start()
    logger.info("Scheduler started: scrape every 2 hours.")

    # Run initial scrape after a short delay
    threading.Timer(5.0, run_scrape_all).start()

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5001, debug=True)
