# -*- coding: utf-8 -*-
"""
SQLite database layer for persistent storage of news, companies, and analysis results.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "monitor.db")


@contextmanager
def get_db():
    """Get a database connection as a context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                summary TEXT,
                content TEXT,
                source TEXT,
                source_type TEXT DEFAULT 'news',
                source_weight REAL DEFAULT 0.5,
                url TEXT,
                published TEXT,
                scraped_at TEXT,

                -- Analysis results
                sentiment TEXT,
                sentiment_score REAL,
                risk_level TEXT,

                -- Enhanced info
                key_facts TEXT,          -- JSON array
                key_numbers TEXT,        -- JSON array
                impact_assessment TEXT,

                -- Social media metrics
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                engagement_score REAL DEFAULT 0,
                content_type TEXT DEFAULT 'article',
                author_influence TEXT,

                -- Meta
                is_processed INTEGER DEFAULT 0,
                is_archived INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS news_companies (
                news_id TEXT REFERENCES news(id) ON DELETE CASCADE,
                company_id TEXT NOT NULL,
                impact_type TEXT DEFAULT 'direct',
                impact_sentiment TEXT,
                PRIMARY KEY (news_id, company_id)
            );

            CREATE TABLE IF NOT EXISTS news_topics (
                news_id TEXT REFERENCES news(id) ON DELETE CASCADE,
                topic_id TEXT NOT NULL,
                PRIMARY KEY (news_id, topic_id)
            );

            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id TEXT REFERENCES news(id) ON DELETE CASCADE,
                company_id TEXT,
                strategy_type TEXT,
                priority TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS target_company (
                id INTEGER PRIMARY KEY,
                company_id TEXT NOT NULL,
                set_at TEXT DEFAULT (datetime('now')),
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS scrape_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                fetched_count INTEGER,
                saved_count INTEGER,
                error_message TEXT,
                scraped_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_news_published ON news(published DESC);
            CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news(sentiment);
            CREATE INDEX IF NOT EXISTS idx_news_risk ON news(risk_level);
            CREATE INDEX IF NOT EXISTS idx_news_source_type ON news(source_type);
            CREATE INDEX IF NOT EXISTS idx_nc_company ON news_companies(company_id);
            CREATE INDEX IF NOT EXISTS idx_nt_topic ON news_topics(topic_id);
        """)
    logger.info("Database initialized at %s", DB_PATH)


def upsert_news(news_item: dict):
    """Insert or update a news item."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO news (
                id, title, summary, content, source, source_type, source_weight,
                url, published, scraped_at,
                sentiment, sentiment_score, risk_level,
                key_facts, key_numbers, impact_assessment,
                likes, comments, shares, views, engagement_score,
                content_type, author_influence, is_processed
            ) VALUES (
                :id, :title, :summary, :content, :source, :source_type, :source_weight,
                :url, :published, :scraped_at,
                :sentiment, :sentiment_score, :risk_level,
                :key_facts, :key_numbers, :impact_assessment,
                :likes, :comments, :shares, :views, :engagement_score,
                :content_type, :author_influence, :is_processed
            )
            ON CONFLICT(id) DO UPDATE SET
                summary = COALESCE(excluded.summary, news.summary),
                sentiment = COALESCE(excluded.sentiment, news.sentiment),
                sentiment_score = COALESCE(excluded.sentiment_score, news.sentiment_score),
                risk_level = COALESCE(excluded.risk_level, news.risk_level),
                key_facts = COALESCE(excluded.key_facts, news.key_facts),
                key_numbers = COALESCE(excluded.key_numbers, news.key_numbers),
                impact_assessment = COALESCE(excluded.impact_assessment, news.impact_assessment),
                likes = COALESCE(excluded.likes, news.likes),
                comments = COALESCE(excluded.comments, news.comments),
                shares = COALESCE(excluded.shares, news.shares),
                is_processed = COALESCE(excluded.is_processed, news.is_processed)
        """, {
            "id": news_item.get("id", ""),
            "title": news_item.get("title", ""),
            "summary": news_item.get("summary", ""),
            "content": news_item.get("content"),
            "source": news_item.get("source", ""),
            "source_type": news_item.get("source_type", "news"),
            "source_weight": news_item.get("source_weight", 0.5),
            "url": news_item.get("url", ""),
            "published": news_item.get("published", ""),
            "scraped_at": news_item.get("scraped_at", datetime.now().isoformat()),
            "sentiment": news_item.get("sentiment"),
            "sentiment_score": news_item.get("sentiment_score"),
            "risk_level": news_item.get("risk_level"),
            "key_facts": json.dumps(news_item.get("key_facts", []), ensure_ascii=False) if news_item.get("key_facts") else None,
            "key_numbers": json.dumps(news_item.get("key_numbers", []), ensure_ascii=False) if news_item.get("key_numbers") else None,
            "impact_assessment": news_item.get("impact_assessment"),
            "likes": news_item.get("platform_metrics", {}).get("likes", 0),
            "comments": news_item.get("platform_metrics", {}).get("comments", 0),
            "shares": news_item.get("platform_metrics", {}).get("shares", 0),
            "views": news_item.get("platform_metrics", {}).get("views", 0),
            "engagement_score": news_item.get("engagement_score", 0),
            "content_type": news_item.get("content_type", "article"),
            "author_influence": news_item.get("author_influence"),
            "is_processed": 1 if news_item.get("sentiment") else 0,
        })

        # Save company associations
        for company_id in news_item.get("companies", []):
            conn.execute("""
                INSERT OR IGNORE INTO news_companies (news_id, company_id, impact_type)
                VALUES (?, ?, 'direct')
            """, (news_item["id"], company_id))

        # Save topic associations
        for topic_id in news_item.get("topics", []):
            conn.execute("""
                INSERT OR IGNORE INTO news_topics (news_id, topic_id)
                VALUES (?, ?)
            """, (news_item["id"], topic_id))


def get_news_list(page=1, per_page=20, sentiment=None, company=None, topic=None, risk=None, source_type=None, search=None):
    """Fetch paginated and filtered news list."""
    with get_db() as conn:
        conditions = ["1=1"]
        params = []

        if sentiment and sentiment != "all":
            conditions.append("n.sentiment = ?")
            params.append(sentiment)
        if risk and risk != "all":
            conditions.append("n.risk_level = ?")
            params.append(risk)
        if source_type and source_type != "all":
            conditions.append("n.source_type = ?")
            params.append(source_type)
        if search:
            conditions.append("(n.title LIKE ? OR n.summary LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        joins = ""
        if company and company != "all":
            joins += " INNER JOIN news_companies nc ON n.id = nc.news_id"
            conditions.append("nc.company_id = ?")
            params.append(company)
        if topic and topic != "all":
            joins += " INNER JOIN news_topics nt ON n.id = nt.news_id"
            conditions.append("nt.topic_id = ?")
            params.append(topic)

        where = " AND ".join(conditions)

        # Count total
        count_sql = f"SELECT COUNT(DISTINCT n.id) FROM news n {joins} WHERE {where}"
        total = conn.execute(count_sql, params).fetchone()[0]

        # Fetch page
        offset = (page - 1) * per_page
        data_sql = f"""
            SELECT DISTINCT n.* FROM news n {joins}
            WHERE {where}
            ORDER BY n.published DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(data_sql, params + [per_page, offset]).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            # Load associated companies
            companies = conn.execute(
                "SELECT company_id FROM news_companies WHERE news_id = ?", (item["id"],)
            ).fetchall()
            item["companies"] = [c["company_id"] for c in companies]

            # Load associated topics
            topics = conn.execute(
                "SELECT topic_id FROM news_topics WHERE news_id = ?", (item["id"],)
            ).fetchall()
            item["topics"] = [t["topic_id"] for t in topics]

            # Parse JSON fields
            for field in ("key_facts", "key_numbers"):
                if item.get(field):
                    try:
                        item[field] = json.loads(item[field])
                    except (json.JSONDecodeError, TypeError):
                        item[field] = []
                else:
                    item[field] = []

            result.append(item)

        return result, total


def get_dashboard_stats():
    """Compute dashboard statistics from the database."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]

        sentiment_rows = conn.execute(
            "SELECT sentiment, COUNT(*) as cnt FROM news GROUP BY sentiment"
        ).fetchall()
        sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
        for row in sentiment_rows:
            if row["sentiment"] in sentiment_dist:
                sentiment_dist[row["sentiment"]] = row["cnt"]

        source_type_rows = conn.execute(
            "SELECT source_type, COUNT(*) as cnt FROM news GROUP BY source_type"
        ).fetchall()
        source_types = {row["source_type"]: row["cnt"] for row in source_type_rows}

        company_rows = conn.execute("""
            SELECT nc.company_id,
                   COUNT(*) as total,
                   SUM(CASE WHEN n.sentiment='positive' THEN 1 ELSE 0 END) as positive,
                   SUM(CASE WHEN n.sentiment='negative' THEN 1 ELSE 0 END) as negative,
                   SUM(CASE WHEN n.sentiment='neutral' THEN 1 ELSE 0 END) as neutral
            FROM news_companies nc
            JOIN news n ON nc.news_id = n.id
            GROUP BY nc.company_id
        """).fetchall()
        company_stats = {}
        for row in company_rows:
            company_stats[row["company_id"]] = {
                "total": row["total"],
                "positive": row["positive"],
                "negative": row["negative"],
                "neutral": row["neutral"],
            }

        topic_rows = conn.execute("""
            SELECT nt.topic_id, COUNT(*) as cnt
            FROM news_topics nt GROUP BY nt.topic_id
        """).fetchall()
        topic_dist = {row["topic_id"]: row["cnt"] for row in topic_rows}

        alerts = conn.execute("""
            SELECT * FROM news
            WHERE risk_level IN ('high', 'medium') AND sentiment = 'negative'
            ORDER BY published DESC LIMIT 20
        """).fetchall()
        alerts_list = [dict(a) for a in alerts]

        return {
            "total_news": total,
            "sentiment_distribution": sentiment_dist,
            "source_types": source_types,
            "company_stats": company_stats,
            "topic_distribution": topic_dist,
            "alerts": alerts_list,
        }


def set_target_company(company_id: str):
    """Set or update the target company."""
    with get_db() as conn:
        conn.execute("UPDATE target_company SET is_active = 0")
        conn.execute("""
            INSERT INTO target_company (company_id, is_active)
            VALUES (?, 1)
        """, (company_id,))


def get_target_company() -> str | None:
    """Get the current active target company ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT company_id FROM target_company WHERE is_active = 1 ORDER BY set_at DESC LIMIT 1"
        ).fetchone()
        return row["company_id"] if row else None


def log_scrape(source: str, fetched: int, saved: int, error: str = None):
    """Log a scraping run."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO scrape_log (source, fetched_count, saved_count, error_message)
            VALUES (?, ?, ?, ?)
        """, (source, fetched, saved, error))
