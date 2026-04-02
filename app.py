# -*- coding: utf-8 -*-
"""
Hong Kong Insurance Sentiment Monitor - Backend
"""

import json
import os
import hashlib
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

MONITORED_COMPANIES = [
    {"id": "aia", "name": "\u53cb\u90a6\u4fdd\u9669", "name_en": "AIA", "aliases": ["\u53cb\u90a6", "AIA", "AIA Group"]},
    {"id": "prudential", "name": "\u4fdd\u8bda\u4fdd\u9669", "name_en": "Prudential", "aliases": ["\u4fdd\u8bda", "Prudential", "\u82f1\u56fd\u4fdd\u8bda"]},
    {"id": "axa", "name": "\u5b89\u76db\u4fdd\u9669", "name_en": "AXA", "aliases": ["\u5b89\u76db", "AXA", "AXA Hong Kong"]},
    {"id": "manulife", "name": "\u5b8f\u5229\u4fdd\u9669", "name_en": "Manulife", "aliases": ["\u5b8f\u5229", "Manulife", "\u5b8f\u5229\u4eba\u5bff"]},
    {"id": "sunlife", "name": "\u6c38\u660e\u91d1\u878d", "name_en": "Sun Life", "aliases": ["\u6c38\u660e", "Sun Life", "\u6c38\u660e\u91d1\u878d"]},
    {"id": "ftlife", "name": "\u5bcc\u901a\u4fdd\u9669", "name_en": "FTLife", "aliases": ["\u5bcc\u901a", "FTLife", "\u5bcc\u901a\u4eba\u5bff"]},
    {"id": "chinlife", "name": "\u4e2d\u56fd\u4eba\u5bff(\u6d77\u5916)", "name_en": "China Life Overseas", "aliases": ["\u4e2d\u56fd\u4eba\u5bff", "China Life", "\u4e2d\u5bff"]},
    {"id": "bochk_life", "name": "\u4e2d\u94f6\u4eba\u5bff", "name_en": "BOCHK Life", "aliases": ["\u4e2d\u94f6\u4eba\u5bff", "BOCHK Life", "\u4e2d\u94f6\u4fdd\u9669"]},
    {"id": "zurich", "name": "\u82cf\u9ece\u4e16\u4fdd\u9669", "name_en": "Zurich", "aliases": ["\u82cf\u9ece\u4e16", "Zurich"]},
    {"id": "generali", "name": "\u5fe0\u610f\u4fdd\u9669", "name_en": "Generali", "aliases": ["\u5fe0\u610f", "Generali"]},
]

TOPIC_CATEGORIES = {
    "claims": {"name": "\u7406\u8d54\u7ea0\u7eb7", "icon": "\u2696\ufe0f", "keywords": ["\u7406\u8d54", "\u62d2\u8d54", "\u8d54\u4ed8", "\u7d22\u8d54", "\u7ea0\u7eb7", "claim", "reject"]},
    "regulation": {"name": "\u76d1\u7ba1\u653f\u7b56", "icon": "\ud83d\udccb", "keywords": ["\u4fdd\u76d1\u5c40", "\u76d1\u7ba1", "\u5408\u89c4", "\u724c\u7167", "IA", "regulation", "compliance", "\u4fdd\u9669\u4e1a\u76d1\u7ba1\u5c40"]},
    "product": {"name": "\u4ea7\u54c1\u53d8\u66f4", "icon": "\ud83d\udce6", "keywords": ["\u65b0\u4ea7\u54c1", "\u505c\u552e", "\u52a0\u8d39", "\u8d39\u7387", "\u6761\u6b3e", "product", "launch", "premium"]},
    "market": {"name": "\u5e02\u573a\u52a8\u6001", "icon": "\ud83d\udcc8", "keywords": ["\u4fdd\u8d39", "\u5e02\u573a\u4efd\u989d", "\u4e1a\u7ee9", "\u589e\u957f", "\u4e0b\u964d", "market", "growth", "revenue"]},
    "complaint": {"name": "\u6295\u8bc9\u8206\u60c5", "icon": "\ud83d\ude24", "keywords": ["\u6295\u8bc9", "\u66dd\u5149", "\u6b3a\u8bc8", "\u8bef\u5bfc", "\u9500\u552e", "complaint", "fraud", "mislead"]},
    "tech": {"name": "\u79d1\u6280\u521b\u65b0", "icon": "\ud83e\udd16", "keywords": ["\u6570\u5b57\u5316", "InsurTech", "\u79d1\u6280", "AI", "\u533a\u5757\u94fe", "digital", "technology"]},
    "cross_border": {"name": "\u8de8\u5883\u4e1a\u52a1", "icon": "\ud83c\udf0f", "keywords": ["\u5185\u5730\u5ba2", "\u5927\u6e7e\u533a", "\u8de8\u5883", "GBA", "mainland", "cross-border", "\u5185\u5730"]},
}

RESPONSE_STRATEGIES = {
    "claims": {
        "high": [
            "\u7acb\u5373\u6210\u7acb\u4e13\u9879\u5e94\u5bf9\u5c0f\u7ec4\uff0c\u7531\u516c\u5173\u90e8\u95e8\u7275\u5934",
            "24\u5c0f\u65f6\u5185\u53d1\u5e03\u5b98\u65b9\u58f0\u660e\uff0c\u5f3a\u8c03\u7406\u8d54\u6d41\u7a0b\u7684\u900f\u660e\u6027",
            "\u4e3b\u52a8\u8054\u7cfb\u6295\u8bc9\u5ba2\u6237\uff0c\u63d0\u4f9bVIP\u901a\u9053\u52a0\u901f\u5904\u7406",
            "\u51c6\u5907Q&A\u6587\u6863\u4f9b\u524d\u7ebf\u9500\u552e\u56e2\u961f\u4f7f\u7528",
            "\u76d1\u6d4b\u540e\u7eed\u8206\u8bba\u8d70\u5411\uff0c\u51c6\u5907\u4e8c\u6b21\u56de\u5e94\u65b9\u6848",
        ],
        "medium": [
            "\u5173\u6ce8\u4e8b\u6001\u53d1\u5c55\uff0c\u51c6\u5907\u5b98\u65b9\u56de\u5e94\u8bdd\u672f",
            "\u5185\u90e8\u6838\u5b9e\u7406\u8d54\u6848\u4ef6\u5177\u4f53\u60c5\u51b5",
            "\u901a\u77e5\u5ba2\u670d\u56e2\u961f\u505a\u597d\u5e94\u5bf9\u51c6\u5907",
        ],
        "low": [
            "\u6301\u7eed\u76d1\u6d4b\uff0c\u65e0\u9700\u7acb\u5373\u884c\u52a8",
            "\u66f4\u65b0\u5185\u90e8FAQ\u77e5\u8bc6\u5e93",
        ],
    },
    "complaint": {
        "high": [
            "\u7d27\u6025\u8054\u7cfb\u6295\u8bc9\u65b9\uff0c\u4e86\u89e3\u8bc9\u6c42",
            "\u6cd5\u52a1\u90e8\u95e8\u4ecb\u5165\u8bc4\u4f30\u98ce\u9669",
            "\u51c6\u5907\u5a92\u4f53\u58f0\u660e\uff0c\u5f3a\u8c03\u5ba2\u6237\u81f3\u4e0a\u7684\u670d\u52a1\u7406\u5ff5",
            "\u542f\u52a8\u5185\u90e8\u8c03\u67e5\u6d41\u7a0b",
            "\u5236\u5b9a\u540e\u7eed\u8ddf\u8fdb\u8ba1\u5212\uff0c\u5b9a\u671f\u5411\u7ba1\u7406\u5c42\u6c47\u62a5",
        ],
        "medium": [
            "\u5ba2\u670d\u90e8\u95e8\u4f18\u5148\u5904\u7406\u76f8\u5173\u6295\u8bc9",
            "\u5206\u6790\u6295\u8bc9\u539f\u56e0\uff0c\u6574\u7406\u6539\u8fdb\u65b9\u6848",
            "\u76d1\u6d4b\u662f\u5426\u6709\u53d1\u9175\u8d8b\u52bf",
        ],
        "low": [
            "\u8bb0\u5f55\u5e76\u5f52\u6863\uff0c\u7eb3\u5165\u6708\u5ea6\u5206\u6790\u62a5\u544a",
        ],
    },
    "regulation": {
        "high": [
            "\u6cd5\u89c4\u5408\u89c4\u56e2\u961f\u7acb\u5373\u8bc4\u4f30\u5f71\u54cd\u8303\u56f4",
            "\u5236\u5b9a\u5408\u89c4\u6574\u6539\u65f6\u95f4\u8868",
            "\u5411\u7ba1\u7406\u5c42\u63d0\u4ea4\u5f71\u54cd\u8bc4\u4f30\u62a5\u544a",
            "\u51c6\u5907\u4e0e\u76d1\u7ba1\u673a\u6784\u7684\u6c9f\u901a\u65b9\u6848",
        ],
        "medium": [
            "\u8ddf\u8e2a\u653f\u7b56\u7ec6\u8282\uff0c\u8bc4\u4f30\u5bf9\u4e1a\u52a1\u7684\u6f5c\u5728\u5f71\u54cd",
            "\u7ec4\u7ec7\u5185\u90e8\u57f9\u8bad\u786e\u4fdd\u56e2\u961f\u77e5\u6089",
        ],
        "low": [
            "\u7eb3\u5165\u884c\u4e1a\u52a8\u6001\u8ffd\u8e2a\uff0c\u5b9a\u671f\u66f4\u65b0",
        ],
    },
    "default": {
        "high": ["\u5bc6\u5207\u5173\u6ce8\u4e8b\u6001\u53d1\u5c55", "\u51c6\u5907\u5b98\u65b9\u56de\u5e94\u65b9\u6848", "\u901a\u77e5\u76f8\u5173\u90e8\u95e8\u505a\u597d\u51c6\u5907"],
        "medium": ["\u6301\u7eed\u76d1\u6d4b", "\u5185\u90e8\u8bc4\u4f30\u5f71\u54cd"],
        "low": ["\u5e38\u89c4\u8bb0\u5f55"],
    },
}


def generate_id(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def detect_sentiment(title, summary):
    text = (title + " " + summary).lower()
    negative_words = [
        "\u6295\u8bc9", "\u62d2\u8d54", "\u6b3a\u8bc8", "\u8bef\u5bfc", "\u4e8f\u635f", "\u4e0b\u964d",
        "\u8d1f\u9762", "\u7ea0\u7eb7", "\u8fdd\u89c4", "\u5904\u7f5a", "\u7f5a\u6b3e", "\u66dd\u5149",
        "\u574e", "\u9a97", "\u9ed1\u5e55", "\u4e11\u95fb", "\u5371\u673a", "\u8bc9\u8bbc",
        "reject", "fraud", "complaint", "scandal", "decline", "loss", "penalty",
        "controversy", "lawsuit", "warning", "risk", "concern",
        "\u95ee\u9898", "\u98ce\u9669", "\u8b66\u544a", "\u53eb\u505c", "\u6574\u6539", "\u5c01\u6740", "\u66b4\u96f7",
    ]
    positive_words = [
        "\u589e\u957f", "\u521b\u65b0", "\u7a81\u7834", "\u9886\u5148", "\u8363\u83b7", "\u5347\u7ea7",
        "\u4f18\u5316", "\u4fbf\u5229",
        "growth", "innovation", "award", "launch", "improve", "benefit",
        "\u5408\u4f5c", "\u5229\u597d", "\u65b0\u9ad8", "\u673a\u9047", "\u7ea2\u5229", "\u56de\u6696",
    ]
    neg_count = sum(1 for w in negative_words if w in text)
    pos_count = sum(1 for w in positive_words if w in text)
    if neg_count > pos_count and neg_count >= 1:
        score = max(-1.0, -0.3 * neg_count)
        return "negative", round(score, 2)
    elif pos_count > neg_count and pos_count >= 1:
        score = min(1.0, 0.3 * pos_count)
        return "positive", round(score, 2)
    else:
        return "neutral", 0.0


def detect_companies(title, summary):
    text = title + " " + summary
    matched = []
    for company in MONITORED_COMPANIES:
        for alias in company["aliases"]:
            if alias.lower() in text.lower():
                matched.append(company["id"])
                break
    return list(set(matched))


def detect_topics(title, summary):
    text = (title + " " + summary).lower()
    matched = []
    for topic_id, topic in TOPIC_CATEGORIES.items():
        for kw in topic["keywords"]:
            if kw.lower() in text:
                matched.append(topic_id)
                break
    return matched if matched else ["market"]


def assess_risk_level(sentiment, sentiment_score, source_weight=1.0):
    if sentiment == "negative":
        if sentiment_score <= -0.6:
            return "high"
        elif sentiment_score <= -0.3:
            return "medium"
    return "low"


def get_strategies(topics, risk_level):
    strategies = []
    for topic in topics:
        topic_strategies = RESPONSE_STRATEGIES.get(topic, RESPONSE_STRATEGIES["default"])
        strategies.extend(topic_strategies.get(risk_level, []))
    return list(dict.fromkeys(strategies))


# Real news data - scraped from web search on 2026-04-02
DEMO_NEWS = [
    {
        "title": "GN16+\u6307\u5f1534\u5b9a\u6863\u843d\u5730\uff0c\u9999\u6e2f\u4fdd\u9669\u4e1a\u8fce\u6765\u91cd\u5927\u8f6c\u53d8",
        "summary": "3\u670831\u65e5\u8d77\uff0c\u9999\u6e2f\u4fdd\u9669\u4e1a\u8fce\u6765\u91cd\u5927\u8f6c\u53d8\u3002\u65b0\u7248\u300a\u627f\u4fdd\u957f\u671f\u4fdd\u9669\u4e1a\u52a1\u6307\u5f15\u300b(GN16)\u4e0e\u4fee\u8ba2\u7248\u300a\u5206\u7ea2\u4e1a\u52a1\u7ba1\u6cbb\u6307\u5f15\u300b(\u6307\u5f1534)\u540c\u6b65\u751f\u6548\uff0c\u5168\u884c\u4e1a\u6700\u4e25\u76d1\u7ba1\u843d\u5730\uff0c\u5f7b\u5e95\u5835\u6b7b\u9500\u552e\u8bef\u5bfc\u3001\u6a21\u7cca\u5206\u7ea2\u6f14\u793a\u7b49\u7a7a\u5b50\u3002\u65b0\u89c4\u8981\u6c42\u4fdd\u9669\u516c\u53f8\u5fc5\u987b\u62ab\u9732\u5206\u7ea2\u5b9e\u73b0\u7387\uff0c\u589e\u5f3a\u4ea7\u54c1\u900f\u660e\u5ea6\u3002",
        "source": "\u817e\u8baf\u65b0\u95fb",
        "url": "https://news.qq.com/rain/a/20260326A07AIW00",
        "published": "2026-03-31T00:00:00",
        "source_weight": 0.9,
    },
    {
        "title": "\u6e2f\u9669\u8fce\u6765\u53f2\u8bd7\u7ea7\u5229\u597d\uff0c\u5185\u5730\u8bbf\u5ba2\u6210\u6700\u5927\u8d62\u5bb6",
        "summary": "\u5185\u5730\u6295\u4fdd\u4eba\u8fce\u6765\u53cc\u91cd\u5229\u597d\uff012026\u5e743\u670831\u65e5\uff0c\u9999\u6e2f\u65b0\u7248GN16+\u6307\u5f1534\u6b63\u5f0f\u751f\u6548\uff0c\u4fdd\u9669\u516c\u53f8\u5fc5\u987b\u5982\u5b9e\u62ab\u9732\u5206\u7ea2\u5b9e\u73b0\u7387\u3001\u4e25\u7981\u5938\u5927\u5ba3\u4f20\uff0c\u9632\u6b62\u9500\u552e\u8bef\u5bfc\u3002\u540c\u65f6\uff0c\u4fdd\u8bda\u62ab\u9732\u9999\u6e2f\u65b0\u4e1a\u52a1\u5229\u6da6\u589e\u957f12%\uff0c\u4f9d\u8d56\u5185\u5730\u6e38\u5ba2\u9500\u552e\u989d\u589e\u957f\u3002\u5927\u6e7e\u533a\u4e92\u8054\u4e92\u901a\u653f\u7b56\u88ab\u89c6\u4e3a\u4e3b\u8981\u63a8\u52a8\u529b\u3002",
        "source": "\u65b0\u6d6a\u8d22\u7ecf",
        "url": "https://finance.sina.com.cn/wm/2026-03-27/doc-inhsmnzu2096049.shtml",
        "published": "2026-03-27T10:00:00",
        "source_weight": 0.9,
    },
    {
        "title": "\u5185\u5730\u8d74\u6e2f\u6295\u4fdd\u4fdd\u8d39\u5fae\u964d\uff0c\u6e2f\u9669\u964d\u6e29\u4e86\uff1f",
        "summary": "\u8fd1\u5e74\u6765\uff0c\u9999\u6e2f\u4fdd\u9669\u56e0\u4ea7\u54c1\u7684\u7075\u6d3b\u6027\u3001\u8f83\u9ad8\u7684\u6295\u8d44\u56de\u62a5\u548c\u591a\u5e01\u79cd\u9009\u62e9\u7b49\u6df1\u53d7\u5185\u5730\u6d88\u8d39\u8005\u559c\u7231\u3002\u4e0d\u8fc7\u6301\u7eed\u9ad8\u6da8\u7684\u6295\u4fdd\u70ed\u60c5\u51fa\u73b0\u5fae\u964d\u8ff9\u8c61\uff0c\u5185\u5730\u8bbf\u5ba2\u65b0\u589e\u4fdd\u8d39\u540c\u6bd4\u51fa\u73b0\u8f7b\u5fae\u4e0b\u964d\uff0c\u5e02\u573a\u5206\u6790\u8ba4\u4e3a\u4e3b\u8981\u53d7\u9ad8\u57fa\u6570\u6548\u5e94\u5f71\u54cd\uff0c\u6574\u4f53\u4ecd\u7ef4\u6301\u8f83\u9ad8\u6c34\u5e73\u3002",
        "source": "\u65b0\u6d6a\u8d22\u7ecf",
        "url": "https://k.sina.cn/article_7857201856_1d45362c001903u5ny.html",
        "published": "2026-04-01T09:00:00",
        "source_weight": 0.85,
    },
    {
        "title": "\u4e70\u6e2f\u9669\u65e0\u9700\u4eb2\u8d74\uff1f\u9999\u6e2f\u62df\u7ec6\u5316\u5185\u5730\u4fdd\u9669\u5ba2\u6237\u5b9a\u4e49",
        "summary": "\u9999\u6e2f\u62df\u7ec6\u5316\u5185\u5730\u4fdd\u9669\u5ba2\u6237\u5b9a\u4e49\uff0c\u63a2\u8ba8\u653e\u5bbd\u5185\u5730\u5ba2\u6237\u8d74\u6e2f\u6295\u4fdd\u8981\u6c42\u3002\u4fdd\u8bda\u8868\u793a2025\u5e74\u9999\u6e2f\u65b0\u4e1a\u52a1\u5229\u6da6\u589e\u957f12%\uff0c\u4f9d\u8d56\u5185\u5730\u6e38\u5ba2\u9500\u552e\u989d\u589e\u957f\u3002\u5185\u5730\u6e38\u5ba2\u5bfb\u6c42\u8d27\u5e01\u53ca\u8d44\u4ea7\u591a\u5143\u5316\u3001\u4f18\u8d28\u533b\u7597\u670d\u52a1\u7b49\u4fdd\u9669\u4ea7\u54c1\uff0c\u5927\u6e7e\u533a\u5e03\u5c40\u88ab\u89c6\u4e3a\u5173\u952e\u3002",
        "source": "\u65b0\u6d6a\u8d22\u7ecf",
        "url": "https://finance.sina.cn/2026-03-18/detail-inhrmtwe1322370.d.html",
        "published": "2026-03-18T08:00:00",
        "source_weight": 0.85,
    },
    {
        "title": "\u53cb\u90a6\u4fdd\u9669\u63a8\u51fa\u300c\u6d3b\u7136\u4eba\u751f\u300dProsperLife\u4fdd\u9669\u8ba1\u5212",
        "summary": "\u53cb\u90a6\u4fdd\u96693\u670831\u65e5\u5ba3\u5e03\u63a8\u51fa\u5168\u65b0\u300c\u6d3b\u7136\u4eba\u751f\u300d\u4fdd\u9669\u8ba1\u5212(ProsperLife Insurance Plan)\uff0c\u63d0\u4f9b\u7ec8\u8eab\u4fdd\u969c\uff0c\u8986\u76d6\u4eba\u751f\u6bcf\u4e2a\u9636\u6bb5\u3002\u8fd9\u662fAIA\u5728\u65b0\u76d1\u7ba1\u6846\u67b6\u4e0b\u63a8\u51fa\u7684\u9996\u6b3e\u91cd\u78c5\u4ea7\u54c1\uff0c\u4e3b\u6253\u7075\u6d3b\u4fdd\u969c\u4e0e\u8d22\u5bcc\u4f20\u627f\u3002",
        "source": "etnet/AIA\u5a92\u4f53\u4e2d\u5fc3",
        "url": "https://www.aia.com.hk/en/about-aia/about-us/media-centre/press-releases",
        "published": "2026-03-31T12:00:00",
        "source_weight": 0.9,
    },
    {
        "title": "\u53cb\u90a6Alta Club\u63a8\u51fa\u300c\u5bb6\u5ead\u5065\u5eb7MedTeam\u300d\uff0c\u9996\u521b24/7\u5c08\u5c5e\u533b\u7597\u652f\u63f4",
        "summary": "\u53cb\u90a6\u4fdd\u9669\u65d7\u4e0bAlta Club\u63a8\u51fa\u300c\u5bb6\u5ead\u5065\u5eb7MedTeam\u300d\uff0c\u8fd9\u662f\u9999\u6e2f\u4fdd\u9669\u5e02\u573a\u9996\u4e2a\u4e3a\u9ad8\u51c0\u503c\u5bb6\u5ead\u63d0\u4f9b24/7\u4e13\u5c5e\u533b\u7597\u652f\u63f4\u7684\u670d\u52a1\uff0c\u6db5\u76d6\u5065\u5eb7\u7ba1\u7406\u3001\u7d27\u6025\u533b\u7597\u534f\u8c03\u3001\u4e13\u5bb6\u8f6c\u4ecb\u7b49\u5168\u65b9\u4f4d\u670d\u52a1\u3002",
        "source": "AIA\u65b0\u95fb\u7a3f",
        "url": "https://www.aia.com.hk/en",
        "published": "2026-02-06T10:00:00",
        "source_weight": 0.8,
    },
    {
        "title": "AXA\u5b89\u76db\u300c2026\u521d\u590f\u4e30\u76db\u8d4f\u300d\u63a8\u5e7f\u8ba1\u5212\u542f\u52a8",
        "summary": "AXA\u5b89\u76db\u4e8e2026\u5e744\u6708\u542f\u52a8\u300c2026\u521d\u590f\u4e30\u76db\u8d4f\u300d\u63a8\u5e7f\u8ba1\u5212\uff0c\u4ea7\u54c1\u6db5\u76d6\u533b\u7597\u53ca\u5371\u75be\u3001\u7a0e\u52a1\u6263\u51cf\u3001\u50a8\u84c4\u4ee5\u53ca\u96c7\u5458\u798f\u5229\u7b49\u591a\u5143\u4ea7\u54c1\u7ebf\uff0c\u662f\u5b89\u76db\u5728\u65b0\u76d1\u7ba1\u73af\u5883\u4e0b\u7684\u91cd\u70b9\u8425\u9500\u6d3b\u52a8\u3002",
        "source": "AXA\u5b98\u7f51",
        "url": "https://www.axa.com.hk/cn/2026-april-campaign",
        "published": "2026-04-01T00:00:00",
        "source_weight": 0.75,
    },
    {
        "title": "\u9999\u6e2f\u4fdd\u9669\u5185\u5730\u5316\uff0c\u4e00\u573a\u201c\u7206\u96f7\u6f6e\u201d\u6b63\u5728\u52a0\u901f\u5230\u6765",
        "summary": "\u968f\u7740\u9999\u6e2f\u4fdd\u9669\u5e02\u573a\u5168\u9762\u7206\u53d1\uff0c2025\u5e74\u4e0a\u534a\u5e74\u957f\u671f\u4e1a\u52a1\u65b0\u5355\u4fdd\u8d39\u589e\u901f\u9ad8\u8fbe55.9%\u3002\u4f46\u4e1a\u5185\u4eba\u58eb\u8b66\u544a\uff0c\u5185\u5730\u5316\u8fd0\u4f5c\u5e26\u6765\u9500\u552e\u8bef\u5bfc\u3001\u5938\u5927\u5206\u7ea2\u3001\u8fdd\u89c4\u8fd4\u4f63\u7b49\u98ce\u9669\u6b63\u5728\u7d2f\u79ef\uff0c\u672a\u6765\u53ef\u80fd\u5f15\u53d1\u5927\u89c4\u6a21\u7406\u8d54\u7ea0\u7eb7\u548c\u6295\u8bc9\u6f6e\u3002",
        "source": "\u65b0\u6d6a\u8d22\u7ecf",
        "url": "https://finance.sina.com.cn/money/insurance/bxdt/2026-02-04/doc-inhksqzw2678196.shtml",
        "published": "2026-04-02T08:00:00",
        "source_weight": 0.9,
    },
    {
        "title": "\u5185\u5730\u4eba\u6295\u4fdd\u9999\u6e2f\u4fdd\u9669\uff0c\u7406\u8d54\u5230\u5e95\u96be\u4e0d\u96be\uff1f2026\u5168\u6d41\u7a0b\u6df1\u5ea6\u89e3\u6790",
        "summary": "\u968f\u7740\u6e2f\u9669\u5e02\u573a\u7206\u53d1\uff0c\u7406\u8d54\u95ee\u9898\u6210\u4e3a\u7126\u70b9\u3002\u91cd\u75be\u3001\u8eab\u6545\u7c7b\u6848\u4ef6\u96c6\u4e2d\u8fdb\u5165\u7406\u8d54\u9ad8\u5cf0\u671f\uff0c\u5e38\u89c1\u62d2\u8d54\u7406\u7531\u5305\u62ec'\u672a\u5982\u5b9e\u544a\u77e5'\u3001\u65e2\u5f80\u75c7\u4e89\u8bae\u3001\u793e\u4fdd\u8bb0\u5f55\u4e0d\u4e00\u81f4\u7b49\u3002\u4e13\u4e1a\u5f8b\u5e08\u62c6\u89e3\u4e86\u7406\u8d54\u7ea0\u7eb7\u7684\u5e38\u89c1\u539f\u56e0\u53ca\u7ef4\u6743\u8def\u5f84\u3002",
        "source": "\u77e5\u4e4e/\u4e13\u4e1a\u5206\u6790",
        "url": "https://www.ingstart.com/blog/45833.html",
        "published": "2026-03-26T14:00:00",
        "source_weight": 0.75,
    },
    {
        "title": "\u9999\u6e2f\u4fdd\u9669\u62d2\u8d54\u6848\u4f8b\uff1a\u4e73\u817a\u764c\u60a3\u8005120\u4e07\u6e2f\u5143\u7d22\u8d54\u88ab\u62d2",
        "summary": "\u4e00\u5bb6\u9999\u6e2f\u4fdd\u9669\u516c\u53f8\u62d2\u7edd\u4e86\u4e00\u4f4d\u4e73\u817a\u764c\u60a3\u8005\u7684120\u4e07\u6e2f\u5143\u7d22\u8d54\uff0c\u7406\u7531\u662f\u5176\u793e\u4fdd\u8bb0\u5f55\u663e\u793a\u6709'\u809d\u786c\u5316'\u75c5\u53f2\u3002\u53e6\u4e00\u4f4d\u5ba2\u6237\u7684100\u4e07\u6e2f\u5143\u7d22\u8d54\u56e0'\u80bf\u5757\u5b58\u572810\u5e74'\u88ab\u89c6\u4e3a\u65e2\u5f80\u75c7\u800c\u88ab\u62d2\u3002\u5f8b\u5e08\u5efa\u8bae\u6295\u4fdd\u524d\u5e94\u5c3d\u53ef\u80fd\u5b8c\u6574\u62ab\u9732\u5065\u5eb7\u4fe1\u606f\u3002",
        "source": "\u77e5\u4e4e",
        "url": "https://zhuanlan.zhihu.com/p/2006444722747613569",
        "published": "2026-03-28T10:00:00",
        "source_weight": 0.7,
    },
    {
        "title": "\u8de8\u5883\u6c47\u6b3e\u5927\u53d8\u9769\uff01\u4e70\u9999\u6e2f\u4fdd\u9669\u6700\u5927\u7684\u98ce\u9669\u51fa\u73b0\u4e86",
        "summary": "2026\u5e741\u67081\u65e5\u8d77\uff0c\u8de8\u5883\u6c47\u6b3e\u4e1a\u52a1\u65b0\u89c4\u751f\u6548\uff0c\u5355\u7b14\u4eba\u6c11\u5e015000\u5143\u6216\u5916\u5e01\u7b49\u503c1000\u7f8e\u5143\u4ee5\u4e0a\u6c47\u6b3e\u9700\u6838\u5b9e\u6c47\u6b3e\u4eba\u4fe1\u606f\u51c6\u786e\u6027\u3002\u6b64\u4e3e\u88ab\u89c6\u4e3a\u76d1\u7ba1\u5c42\u5bf9\u8de8\u5883\u6295\u4fdd\u8d44\u91d1\u6d41\u52a8\u7684\u8fdb\u4e00\u6b65\u6536\u7d27\uff0c\u53ef\u80fd\u5f71\u54cd\u5185\u5730\u5ba2\u7f34\u8d39\u4fbf\u5229\u6027\u3002",
        "source": "\u96ea\u7403",
        "url": "https://xueqiu.com/7318086163/364773856",
        "published": "2026-03-29T08:00:00",
        "source_weight": 0.75,
    },
    {
        "title": "\u7ca4\u6e2f\u6fb3\u56fd\u9645\u533b\u7597\u670d\u52a1\u4e0e\u8de8\u5883\u5546\u4fdd\u652f\u4ed8\u878d\u5408\u7814\u8ba8\u4f1a\u53ec\u5f00",
        "summary": "3\u670828\u65e5\uff0c\u5e7f\u4e1c\u770125\u5bb6\u56fd\u9645\u533b\u7597\u670d\u52a1\u8bd5\u70b9\u533b\u9662\u4ee3\u8868\u9f50\u805a\u9999\u6e2f\u5927\u5b66\u6df1\u5733\u533b\u9662\uff0c\u5171\u540c\u63a2\u8ba8\u8de8\u5883\u5546\u4fdd\u652f\u4ed8\u878d\u5408\u3001\u4e00\u5c0f\u65f6\u4f18\u8d28\u533b\u7597\u670d\u52a1\u5708\u5efa\u8bbe\u3002\u8fd9\u6807\u5fd7\u7740\u5927\u6e7e\u533a\u4fdd\u9669\u4e0e\u533b\u7597\u4e92\u8054\u4e92\u901a\u8fdb\u5165\u5b9e\u8d28\u6027\u63a8\u8fdb\u9636\u6bb5\u3002",
        "source": "\u6df1\u5733\u65b0\u95fb\u7f51",
        "url": "https://www.sznews.com/news/content/2026-03/30/content_31997382.htm",
        "published": "2026-03-30T10:00:00",
        "source_weight": 0.8,
    },
    {
        "title": "\u9999\u6e2f\u4fdd\u9669\u516c\u53f8\u5206\u7ea2\u5b9e\u73b0\u7387\u5bf9\u6bd4\uff1a\u4fdd\u8bda\u6700\u4f4e\u4ec53%",
        "summary": "\u6700\u65b0\u5206\u7ea2\u5b9e\u73b0\u7387\u5bf9\u6bd4\u663e\u793a\uff0c\u53cb\u90a6\u76c8\u5fa1\u591a\u5143\u8d27\u5e01\u8ba1\u5212\u8fde\u7eed3\u5e74\u8fbe100%\uff0c\u8868\u73b0\u4f18\u5f02\uff1b\u5b8f\u52295\u5e74\u671f\u4ea7\u54c147\u5e74\u624d\u89e6\u9876\uff0c\u62cd\u6240\u611a\u5bd3\uff1b\u4fdd\u8bda\u90e8\u5206\u4ea7\u54c1\u5206\u7ea2\u5b9e\u73b0\u7387\u6700\u4f4e\u4ec53%\uff0c\u5f15\u53d1\u5e02\u573a\u62c5\u5fe7\u3002\u4e13\u4e1a\u5206\u6790\u8ba4\u4e3a\u9009\u62e9\u4fdd\u9669\u516c\u53f8\u65f6\u5206\u7ea2\u5b9e\u73b0\u7387\u662f\u5173\u952e\u6307\u6807\u3002",
        "source": "\u4f1a\u8ba1\u5b66\u5802",
        "url": "https://www.acc5.com/news-xinwen/detail_216847.html",
        "published": "2026-03-30T08:00:00",
        "source_weight": 0.7,
    },
    {
        "title": "\u6e2f\u9669\u7518\u9009\u6307\u5357\uff1a12\u5bb6\u5934\u90e8\u4fdd\u9669\u516c\u53f8\u6838\u5fc3\u4f18\u52bf\u5bf9\u6bd4",
        "summary": "\u9999\u6e2f\u4fdd\u9669\u5e02\u57372025\u5e74\u524d\u4e09\u5b63\u5ea6\u4fdd\u8d39\u8fbe2645\u4ebf\u6e2f\u5143\uff0c\u540c\u6bd4\u98d9\u534755.9%\u3002\u63ed\u79d812\u5bb6\u9876\u5c16\u4fdd\u53f8\u6838\u5fc3\u4f18\u52bf\uff1a\u53cb\u90a6\u5168\u7403\u5316\u5e03\u5c40\u3001\u4fdd\u8bda\u82f1\u5f0f\u5206\u7ea2\u9f3b\u7956\u3001\u5b8f\u5229\u79d1\u6280\u7406\u8d545\u5206\u949f\u5230\u8d26\u3001\u5b89\u76db\u533b\u7597\u7f51\u7edc\u8986\u76d6\u5e7f\u3002\u9ad8\u51c0\u503c\u4e0e\u4e2d\u4ea7\u5ba2\u6237\u9f50\u6d8c\u5165\u3002",
        "source": "\u767e\u5ea6",
        "url": "https://baijiahao.baidu.com/s?id=1860923826957890512",
        "published": "2026-03-28T14:00:00",
        "source_weight": 0.7,
    },
    {
        "title": "2026\u5e74\u8fd8\u80fd\u4e70\u9999\u6e2f\u4fdd\u9669\u5417\uff1f\u6700\u65b0\u653f\u7b56\u89e3\u8bfb",
        "summary": "2026\u5e74\u9999\u6e2f\u4fdd\u9669\u76d1\u7ba1\u5347\u7ea7\u3001\u653f\u7b56\u4f18\u5316\uff0c\u4e0d\u5c11\u4eba\u7591\u60d1\u73b0\u5728\u8fd8\u80fd\u4e0d\u80fd\u4e70\u3002\u4e13\u4e1a\u5206\u6790\u8ba4\u4e3a\uff0c\u9999\u6e2f\u4fdd\u9669\u4ecd\u53ef\u5408\u6cd5\u6295\u4fdd\uff0c\u4e14\u653f\u7b56\u66f4\u89c4\u8303\u3001\u670d\u52a1\u66f4\u4fbf\u6377\u3002\u7ed3\u5408\u65b0\u89c4GN16\u548c\u62a5\u884c\u5408\u4e00\u653f\u7b56\uff0c\u4fdd\u9669\u4ea7\u54c1\u900f\u660e\u5ea6\u548c\u6d88\u8d39\u8005\u4fdd\u62a4\u5747\u5927\u5e45\u63d0\u5347\u3002",
        "source": "\u4e2d\u8fdc\u8d22\u8baf",
        "url": "http://www.coscoxh.com/?p=9307",
        "published": "2026-03-19T10:00:00",
        "source_weight": 0.65,
    },
    {
        "title": "\u4fdd\u9669\u4e1a\u76d1\u7ba1\u5c40\u53d1\u5e03\u6700\u65b0\u65b0\u95fb\u7a3f\uff0c\u52a0\u5f3a\u884c\u4e1a\u89c4\u7ba1\u529b\u5ea6",
        "summary": "\u9999\u6e2f\u4fdd\u9669\u4e1a\u76d1\u7ba1\u5c40(IA)2026\u5e743\u6708\u53d1\u5e03\u591a\u9879\u65b0\u95fb\u7a3f\uff0c\u5185\u5bb9\u6db5\u76d6\u76d1\u7ba1\u6307\u5f15\u66f4\u65b0\u3001\u884c\u4e1a\u5408\u89c4\u8981\u6c42\u3001\u4ee5\u53ca\u4fdd\u9669\u4e2d\u4ecb\u4eba\u76d1\u7ba1\u7b49\u65b9\u9762\u3002\u8fd9\u8868\u660e\u76d1\u7ba1\u5c42\u6b63\u5728\u52a0\u5927\u5bf9\u884c\u4e1a\u7684\u89c4\u8303\u529b\u5ea6\uff0c\u4ee5\u4fdd\u62a4\u6d88\u8d39\u8005\u6743\u76ca\u3002",
        "source": "\u9999\u6e2f\u4fdd\u76d1\u5c40\u5b98\u7f51",
        "url": "https://www.ia.org.hk/sc/infocenter/press_releases.html",
        "published": "2026-03-02T09:00:00",
        "source_weight": 0.95,
    },
    {
        "title": "\u4fdd\u8bda\u4f9d\u8d56\u5185\u5730\u6e38\u5ba2\u9500\u552e\u589e\u957f\uff0c\u9999\u6e2f\u65b0\u4e1a\u52a1\u5229\u6da6\u589e12%",
        "summary": "\u4fdd\u8bda\u8868\u793a2025\u5e74\u9999\u6e2f\u65b0\u4e1a\u52a1\u5229\u6da6\u589e\u957f12%\uff0c\u5065\u5eb7\u53ca\u4fdd\u969c\u4e1a\u52a1\u5360\u6bd4\u589e\u52a0\u5e26\u52a8\u9500\u552e\u52a8\u80fd\u52a0\u901f\u53ca\u5229\u6da6\u7387\u63d0\u5347\uff0c\u65b0\u4e1a\u52a1\u5229\u6da6\u589e\u957f\u9ad8\u8fbe15%\u3002\u4f5c\u4e3a\u9996\u5bb6\u62ab\u9732\u8d85\u8fc720\u5e74\u5206\u7ea2\u4ea7\u54c1\u5b9e\u9645\u5e73\u5747\u56de\u62a5\u7387\u7684\u516c\u53f8\uff0c\u4fdd\u8bda\u7684\u900f\u660e\u5ea6\u53d7\u5230\u5e02\u573a\u80af\u5b9a\u3002",
        "source": "\u641c\u72d0\u8d22\u7ecf",
        "url": "https://www.sohu.com/a/876045857_121779857",
        "published": "2026-03-26T10:00:00",
        "source_weight": 0.8,
    },
    {
        "title": "\u7ca4\u6e2f\u6fb3\u5927\u6e7e\u533a\u5916\u5546\u4fdd\u9669\u670d\u52a1\u4e2d\u5fc3\u5728\u6a2a\u7434\u63ed\u724c",
        "summary": "\u5e73\u5b89\u4ea7\u9669\u7ca4\u6e2f\u6fb3\u5927\u6e7e\u533a\u5916\u5546\u4fdd\u9669\u670d\u52a1\u4e2d\u5fc3\u5728\u6a2a\u7434\u7ca4\u6fb3\u6df1\u5ea6\u5408\u4f5c\u533a\u63ed\u724c\uff0c\u4e3a\u8de8\u5883\u4fdd\u9669\u670d\u52a1\u63d0\u4f9b\u65b0\u6e20\u9053\u3002\u8fd9\u662f\u5927\u6e7e\u533a\u4fdd\u9669\u4e1a\u4e92\u8054\u4e92\u901a\u7684\u91cd\u8981\u91cc\u7a0b\u7891\uff0c\u672a\u6765\u5c06\u4e3a\u6301\u6709\u9999\u6e2f\u4fdd\u5355\u7684\u5927\u6e7e\u533a\u5c45\u6c11\u63d0\u4f9b\u66f4\u4fbf\u6377\u7684\u552e\u540e\u670d\u52a1\u3002",
        "source": "\u817e\u8baf\u65b0\u95fb",
        "url": "https://news.qq.com/rain/a/20251225A05NRD00",
        "published": "2026-03-25T09:00:00",
        "source_weight": 0.85,
    },
    {
        "title": "\u9999\u6e2f\u4fdd\u9669\u6295\u8bc9\u5c4020\u5e74\u88c1\u51b3\u6848\u4f8b\u8d8b\u52bf\u5206\u6790\uff1a\u672a\u544a\u77e5\u4e89\u8bae\u5360\u6bd422%",
        "summary": "\u5927\u6210\u5f8b\u5e08\u4e8b\u52a1\u6240\u7edf\u8ba12004\u5e74\u81f32023\u5e74\u9999\u6e2f\u4fdd\u9669\u6295\u8bc9\u5c40\u53d7\u7406\u76846530\u4ef6\u7406\u8d54\u6295\u8bc9\u6848\u4ef6\uff0c\u672a\u5982\u5b9e\u544a\u77e5\u5f15\u8d77\u7684\u4e89\u8bae\u6848\u4ef6\u65701461\u4ef6\uff0c\u5360\u6bd422.37%\u3002\u8fd9\u663e\u793a'\u672a\u544a\u77e5'\u662f\u6700\u5e38\u89c1\u7684\u7406\u8d54\u7ea0\u7eb7\u7c7b\u578b\u4e4b\u4e00\uff0c\u6295\u4fdd\u4eba\u5e94\u5f15\u8d77\u91cd\u89c6\u3002",
        "source": "\u5927\u6210\u5f8b\u5e08/\u5934\u6761",
        "url": "https://www.toutiao.com/article/7515829218631025171/",
        "published": "2026-03-27T14:00:00",
        "source_weight": 0.8,
    },
    {
        "title": "\u9999\u6e2fCRS 2.0\u6761\u4f8b\u8349\u68484\u67081\u65e5\u63d0\u4ea4\u7acb\u6cd5\u4f1a\u9996\u8bfb\uff0c\u8de8\u5883\u8d44\u4ea7\u900f\u660e\u65f6\u4ee3\u6765\u4e34",
        "summary": "\u9999\u6e2f\u300a2026\u5e74\u7a0e\u52a1(\u4fee\u8ba2)(\u81ea\u52a8\u4ea4\u6362\u8d44\u6599)\u6761\u4f8b\u8349\u6848\u300b4\u67081\u65e5\u6b63\u5f0f\u63d0\u4ea4\u7acb\u6cd5\u4f1a\u9996\u8bfb\uff0c\u6807\u5fd7\u7740CRS 2.0\u8fc8\u5165\u6b63\u5f0f\u7acb\u6cd5\u843d\u5730\u9636\u6bb5\u3002\u65b0\u89c4\u5c06\u52a0\u5bc6\u8d27\u5e01\u3001\u6570\u5b57\u8d44\u4ea7\u7eb3\u5165\u81ea\u52a8\u4ea4\u6362\u8303\u56f4\uff0c\u5bf9\u6301\u6709\u9999\u6e2f\u4fdd\u5355\u7684\u5185\u5730\u5ba2\u6237\u7a0e\u52a1\u62ab\u9732\u8981\u6c42\u5c06\u66f4\u4e3a\u4e25\u683c\uff0c\u9884\u8ba12027\u5e741\u67081\u65e5\u751f\u6548\u3002",
        "source": "\u540c\u82b1\u987a/\u96ea\u7403",
        "url": "https://xueqiu.com/9669381025/382274104",
        "published": "2026-04-01T14:00:00",
        "source_weight": 0.9,
    },
    {
        "title": "CRS 2.0\u5347\u7ea7\u5728\u5373\uff0c\u9ad8\u51c0\u503c\u4eba\u7fa4\u8de8\u5883\u4fdd\u9669\u67b6\u6784\u9762\u4e34\u8c03\u6574",
        "summary": "\u968f\u7740\u9999\u6e2fCRS 2.0\u7acb\u6cd5\u63a8\u8fdb\uff0c\u4ece'\u4fe1\u606f\u4ea4\u6362'\u5230'\u5168\u9762\u7a7f\u900f'\u5347\u7ea7\uff0c\u9ad8\u51c0\u503c\u4eba\u7fa4\u6301\u6709\u7684\u79bb\u5cb8\u516c\u53f8\u3001\u4fe1\u6258\u67b6\u6784\u3001\u9999\u6e2f\u4fdd\u9669\u7b49\u91d1\u878d\u8d44\u4ea7\u90fd\u5c06\u88ab\u7a7f\u900f\u62ab\u9732\u3002\u4e13\u5bb6\u5efa\u8bae\u63d0\u524d\u542f\u52a8\u5408\u89c4\u8c03\u6574\uff0c\u907f\u514d\u88ab\u52a8\u8865\u7a0e\u548c\u7f34\u7eb3\u6ede\u7eb3\u91d1\u3002",
        "source": "\u641c\u72d0\u8d22\u7ecf",
        "url": "https://www.sohu.com/a/1003819143_121178970",
        "published": "2026-04-01T10:00:00",
        "source_weight": 0.85,
    },
    {
        "title": "CoverGo\u4e3a\u5fe0\u610f\u4fdd\u9669\u9999\u6e2f\u90e8\u7f72AI\u667a\u80fd\u6587\u6863\u5904\u7406\u7cfb\u7edf",
        "summary": "\u4fdd\u9669\u79d1\u6280\u516c\u53f8CoverGo\u4e3a\u5fe0\u610f\u4fdd\u9669\u9999\u6e2f\u90e8\u7f72\u4e86\u667a\u80fd\u6587\u6863\u5904\u7406(IDP)AI Agent\uff0c\u81ea\u52a8\u5316\u5904\u7406\u5065\u5eb7\u4fdd\u9669\u7406\u8d54\uff0c\u663e\u8457\u63d0\u5347\u5904\u7406\u901f\u5ea6\u3001\u51c6\u786e\u6027\u548c\u5ba2\u6237\u4f53\u9a8c\u3002\u8fd9\u662f\u9999\u6e2f\u4fdd\u9669\u4e1aAI\u5e94\u7528\u7684\u6700\u65b0\u6848\u4f8b\u3002",
        "source": "FinTech Global",
        "url": "https://fintech.global/category/sector-updates/insurtech-news/",
        "published": "2026-03-27T08:00:00",
        "source_weight": 0.75,
    },
    {
        "title": "\u4e9a\u592a\u5065\u5eb7\u4fdd\u9669\u521b\u65b0\u5927\u4f1a(HIIC 2026)\u5728\u6e2f\u5706\u6ee1\u843d\u5e55",
        "summary": "\u7b2c\u4e03\u5c4a\u4e9a\u592a\u5065\u5eb7\u4fdd\u9669\u521b\u65b0\u5927\u4f1a(HIIC 2026)\u4e0e\u5927\u6e7e\u533a\u533b\u7597\u5065\u5eb7\u4fc3\u8fdb\u4f1a(GBAHA)\u8054\u5408\u4e3e\u529e\uff0c\u4e8e3\u670826\u65e5\u5728\u9999\u6e2f\u4e5d\u9f99\u9999\u683c\u91cc\u62c9\u9152\u5e97\u5706\u6ee1\u843d\u5e55\u3002\u5927\u4f1a\u805a\u7126AI\u9a71\u52a8\u7684\u5065\u5eb7\u4fdd\u9669\u521b\u65b0\uff0c\u63a2\u8ba8\u6570\u5b57\u5316\u7406\u8d54\u3001\u8de8\u5883\u533b\u7597\u4fdd\u9669\u7b49\u524d\u6cbf\u8bdd\u9898\u3002",
        "source": "GBAHA",
        "url": "https://www.greaterbayhealthcare.com/zh/post/gbaha-2026-%E5%B9%B4%E6%9C%83%E6%94%9C%E6%89%8B-hiic-asia-2026-%E6%8E%A8%E5%8B%95-ai-%E9%A9%85%E5%8B%95%E5%81%A5%E5%BA%B7%E4%BF%9D%E9%9A%AA%E5%B0%8D%E8%A9%B1",
        "published": "2026-03-26T18:00:00",
        "source_weight": 0.75,
    },
    {
        "title": "\u9999\u6e2f\u4fdd\u9669\u5e02\u573a\u6df1\u5ea6\u5206\u6790\u62a5\u544a\uff1a\u673a\u9047\u4e0e\u6311\u6218\u5e76\u5b58",
        "summary": "\u6700\u65b0\u53d1\u5e03\u7684\u9999\u6e2f\u4fdd\u9669\u5e02\u573a\u6df1\u5ea6\u5206\u6790\u62a5\u544a\u6307\u51fa\uff0c\u5e02\u573a\u5728\u9ad8\u901f\u589e\u957f\u7684\u540c\u65f6\u9762\u4e34\u591a\u91cd\u6311\u6218\uff1a\u9500\u552e\u8bef\u5bfc\u98ce\u9669\u7d2f\u79ef\u3001\u5206\u7ea2\u5b9e\u73b0\u7387\u5dee\u5f02\u5927\u3001\u8de8\u5883\u76d1\u7ba1\u534f\u8c03\u96be\u5ea6\u3001\u4ee5\u53caRBC\u5236\u5ea6\u8fc7\u6e21\u671f\u7684\u5408\u89c4\u538b\u529b\u3002\u62a5\u544a\u5efa\u8bae\u6295\u4fdd\u4eba\u91cd\u70b9\u5173\u6ce8\u4fdd\u9669\u516c\u53f8\u5206\u7ea2\u5b9e\u73b0\u7387\u548c\u8d22\u52a1\u8bc4\u7ea7\u3002",
        "source": "tsight.io",
        "url": "https://tsight.io/articles/7211258",
        "published": "2026-03-30T16:00:00",
        "source_weight": 0.8,
    },
    {
        "title": "\u9999\u6e2f\u4fdd\u9669\u534a\u5e74\u72c2\u63fd1737\u4ebf\uff0c\u5934\u90e8\u516c\u53f8\u6392\u540d\u5927\u6d17\u724c",
        "summary": "\u9999\u6e2f\u4fdd\u76d1\u5c40\u516c\u5e03\u7684\u6570\u636e\u663e\u793a\uff0c2025\u5e74\u4e0a\u534a\u5e74\u4e2a\u4eba\u65b0\u5355\u603b\u4fdd\u8d39\u7a81\u78341737\u4ebf\u6e2f\u5143\uff0c\u540c\u6bd4\u6fc0\u589e50.5%\u3002\u5934\u90e8\u516c\u53f8\u6392\u540d\u53d1\u751f\u53d8\u5316\uff0c\u53cb\u90a6\u7a33\u5c45\u7b2c\u4e00\uff0c\u5bcc\u536b\u4eba\u5bff\u4ee5\u6da8291%\u5f3a\u52bf\u4e0a\u5347\uff0c\u5b8f\u5229\u7ecf\u7eaa\u6e20\u9053\u8868\u73b0\u7a81\u51fa\u3002",
        "source": "\u641c\u72d0/\u77e5\u4e4e",
        "url": "https://www.sohu.com/a/948377675_120629828",
        "published": "2026-03-29T10:00:00",
        "source_weight": 0.85,
    },
    {
        "title": "2026\u65b0\u89c4\u843d\u5730\uff0c\u9999\u6e2f\u4fdd\u9669IRR\u8d856%\u662f\u9999\u997c\u8fd8\u662f\u9677\u9631\uff1f",
        "summary": "\u9999\u6e2f\u4fdd\u9669\u5e02\u573a\u90e8\u5206\u4ea7\u54c1\u5ba3\u79f0IRR(\u5185\u90e8\u6536\u76ca\u7387)\u8d856%\uff0c\u4f46\u4e13\u4e1a\u4eba\u58eb\u8b66\u544a\uff1a\u9ad8\u6536\u76ca\u80cc\u540e\u6761\u6b3e\u590d\u6742\uff0c\u6c47\u7387\u6ce2\u52a8\u98ce\u9669\u4e0d\u5bb9\u5ffd\u89c6\uff0c\u4e14\u9700\u6301\u6709\u6570\u5341\u5e74\u751a\u81f3\u767e\u5e74\u624d\u80fd\u5b9e\u73b0\u9884\u671f\u56de\u62a5\u3002\u5efa\u8bae\u6295\u4fdd\u4eba\u4ed4\u7ec6\u7814\u7a76\u5206\u7ea2\u5b9e\u73b0\u7387\u800c\u975e\u53ea\u770b\u6f14\u793a\u6570\u636e\u3002",
        "source": "\u767e\u5ea6",
        "url": "https://www.10100.com/article/39720491",
        "published": "2026-03-31T14:00:00",
        "source_weight": 0.7,
    },
    {
        "title": "\u4fdd\u76d1\u5c40AI Cohort\u8ba1\u5212\u63a8\u52a8\u4fdd\u9669\u4e1a\u6570\u5b57\u5316\u8f6c\u578b",
        "summary": "\u9999\u6e2f\u4fdd\u9669\u4e1a\u76d1\u7ba1\u5c40\u63a8\u51fa\u7684AI Cohort\u8ba1\u5212\u6301\u7eed\u63a8\u8fdb\uff0c\u65e8\u5728\u63a8\u52a8\u4fdd\u9669\u4e1a\u8de8\u5b66\u79d1\u5408\u4f5c\uff0c\u52a0\u901f\u6570\u5b57\u5316\u57fa\u7840\u8bbe\u65bd\u5efa\u8bbe\u3002\u591a\u5bb6\u4fdd\u9669\u516c\u53f8\u53c2\u4e0e\u8bd5\u70b9\uff0c\u63a2\u7d22AI\u5728\u6838\u4fdd\u3001\u7406\u8d54\u3001\u5ba2\u670d\u7b49\u73af\u8282\u7684\u5e94\u7528\u3002",
        "source": "\u9999\u6e2f\u4fdd\u76d1\u5c40",
        "url": "https://www.ia.org.hk/en/infocenter/press_releases/20250818.html",
        "published": "2026-03-28T09:00:00",
        "source_weight": 0.9,
    },
    {
        "title": "\u5fb7\u52e4\u53d1\u5e032026\u5e74\u4fdd\u9669\u4e1a\u5c55\u671b\uff0c\u805a\u7126\u6570\u5b57\u5316\u8f6c\u578b",
        "summary": "\u5fb7\u52e4\u5728\u9999\u6e2fInsurtech Insights Asia\u5927\u4f1a\u4e0a\u53d1\u5e032026\u5e74\u4fdd\u9669\u4e1a\u5c55\u671b\u62a5\u544a\uff0c\u6307\u51fa\u6570\u5b57\u5316\u8f6c\u578b\u3001AI\u5e94\u7528\u3001ESG\u6574\u5408\u548c\u8de8\u5883\u4e1a\u52a1\u5c06\u662f2026\u5e74\u9999\u6e2f\u4fdd\u9669\u5e02\u573a\u7684\u56db\u5927\u5173\u952e\u8d8b\u52bf\u3002",
        "source": "Deloitte",
        "url": "https://www.deloitte.com/cn/en/Industries/insurance/perspectives/2026-insurance-industry-outlook.html",
        "published": "2026-03-25T12:00:00",
        "source_weight": 0.85,
    },
    {
        "title": "\u4fdd\u8bda\u300c\u4fe1\u5b88\u660e\u5929\u300d\u5347\u7ea7\u540e\u6536\u76ca\u5bf9\u6bd4\uff1a28\u5e74\u8fbeIRR 6.5%",
        "summary": "\u4fdd\u8bda\u65b0\u5347\u7ea7\u7684\u300c\u4fe1\u5b88\u660e\u5929\u300d\u50a8\u84c4\u9669\u4e0e\u53cb\u90a6\u3001\u5b8f\u5229\u4e09\u5de8\u5934\u6a2a\u8bc4\u663e\u793a\uff0c\u8be5\u4ea7\u54c128\u5e74\u53ef\u8fbe\u5230\u9884\u671fIRR 6.5%\uff0c5/6/7\u5e74\u63d0\u9886\u573a\u666f\u8868\u73b0\u9886\u5148\uff0c\u4f46\u8d27\u5e01\u8f6c\u6362\u529f\u80fd\u6697\u85cf\u5747\u8861\u98ce\u9669\u3002\u5e02\u573a\u5206\u6790\u8ba4\u4e3a\u5e94\u5168\u9762\u5bf9\u6bd4\u800c\u975e\u53ea\u770b\u5355\u4e00\u6307\u6807\u3002",
        "source": "\u4f1a\u8ba1\u5b66\u5802",
        "url": "https://www.acc5.com/news-xinwen/detail_216286.html",
        "published": "2026-03-29T14:00:00",
        "source_weight": 0.7,
    },
]


def process_news(news_list):
    processed = []
    for news in news_list:
        sentiment, score = detect_sentiment(news["title"], news["summary"])
        companies = detect_companies(news["title"], news["summary"])
        topics = detect_topics(news["title"], news["summary"])
        risk_level = assess_risk_level(sentiment, score, news.get("source_weight", 1.0))
        strategies = get_strategies(topics, risk_level) if sentiment == "negative" else []
        processed.append({
            "id": generate_id(news["title"]),
            "title": news["title"],
            "summary": news["summary"],
            "source": news["source"],
            "url": news.get("url", "#"),
            "published": news["published"],
            "sentiment": sentiment,
            "sentiment_score": score,
            "companies": companies,
            "topics": topics,
            "risk_level": risk_level,
            "strategies": strategies,
        })
    processed.sort(key=lambda x: x["published"], reverse=True)
    return processed


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/news")
def get_news():
    sentiment_filter = request.args.get("sentiment")
    company_filter = request.args.get("company")
    topic_filter = request.args.get("topic")
    risk_filter = request.args.get("risk")
    processed = process_news(DEMO_NEWS)
    if sentiment_filter and sentiment_filter != "all":
        processed = [n for n in processed if n["sentiment"] == sentiment_filter]
    if company_filter and company_filter != "all":
        processed = [n for n in processed if company_filter in n["companies"]]
    if topic_filter and topic_filter != "all":
        processed = [n for n in processed if topic_filter in n["topics"]]
    if risk_filter and risk_filter != "all":
        processed = [n for n in processed if n["risk_level"] == risk_filter]
    return jsonify({"success": True, "data": processed, "total": len(processed)})


@app.route("/api/dashboard")
def get_dashboard():
    processed = process_news(DEMO_NEWS)
    sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
    for n in processed:
        sentiment_dist[n["sentiment"]] += 1
    company_stats = {}
    for company in MONITORED_COMPANIES:
        company_news = [n for n in processed if company["id"] in n["companies"]]
        if company_news:
            pos = sum(1 for n in company_news if n["sentiment"] == "positive")
            neg = sum(1 for n in company_news if n["sentiment"] == "negative")
            neu = sum(1 for n in company_news if n["sentiment"] == "neutral")
            company_stats[company["id"]] = {
                "name": company["name"],
                "name_en": company["name_en"],
                "total": len(company_news),
                "positive": pos,
                "negative": neg,
                "neutral": neu,
            }
    topic_dist = {}
    for tid, tinfo in TOPIC_CATEGORIES.items():
        count = sum(1 for n in processed if tid in n["topics"])
        if count > 0:
            topic_dist[tid] = {"name": tinfo["name"], "icon": tinfo["icon"], "count": count}
    alerts = [n for n in processed if n["risk_level"] in ("high", "medium") and n["sentiment"] == "negative"]
    return jsonify({
        "success": True,
        "data": {
            "total_news": len(processed),
            "sentiment_distribution": sentiment_dist,
            "company_stats": company_stats,
            "topic_distribution": topic_dist,
            "alerts": alerts,
            "last_updated": datetime.now().isoformat(),
        },
    })


@app.route("/api/companies")
def get_companies():
    return jsonify({"success": True, "data": MONITORED_COMPANIES})


@app.route("/api/topics")
def get_topics():
    return jsonify({
        "success": True,
        "data": {k: {"name": v["name"], "icon": v["icon"]} for k, v in TOPIC_CATEGORIES.items()},
    })


@app.route("/api/strategies/<news_id>")
def get_strategies_for_news(news_id):
    processed = process_news(DEMO_NEWS)
    news = next((n for n in processed if n["id"] == news_id), None)
    if not news:
        return jsonify({"success": False, "error": "News not found"}), 404
    return jsonify({
        "success": True,
        "data": {
            "news": news,
            "strategies": news["strategies"],
            "risk_level": news["risk_level"],
        },
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="127.0.0.1")
