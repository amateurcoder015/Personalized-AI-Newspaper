import json
import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from .models import Article, Story, Edition, LLMUsageLog, ConceptUsage


class DatabaseManager:
    def __init__(self, db_path: str = "data/newspaper.db"):
        self.db_path = db_path
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Articles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    content TEXT,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    author TEXT,
                    published_at TEXT,
                    category TEXT,
                    sector TEXT DEFAULT 'General',
                    image_url TEXT,
                    topics TEXT,
                    hash TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Stories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    headline TEXT NOT NULL,
                    summary TEXT,
                    why_it_matters TEXT,
                    category TEXT,
                    sector TEXT DEFAULT 'General',
                    importance_score REAL,
                    relevance_score REAL,
                    final_score REAL,
                    sources TEXT,
                    sources_with_urls TEXT DEFAULT '[]',
                    topics TEXT,
                    matched_watchlist TEXT,
                    evidence_level TEXT DEFAULT 'HIGH CONFIDENCE',
                    is_primary_source INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

            # Article - Story relationships
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_stories (
                    story_id TEXT NOT NULL,
                    article_id TEXT NOT NULL,
                    PRIMARY KEY (story_id, article_id),
                    FOREIGN KEY (story_id) REFERENCES stories(id),
                    FOREIGN KEY (article_id) REFERENCES articles(id)
                )
            """)

            # Editions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS editions (
                    edition_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    html_path TEXT NOT NULL,
                    pdf_path TEXT DEFAULT '',
                    status TEXT NOT NULL,
                    stories_count INTEGER DEFAULT 0,
                    what_changed TEXT DEFAULT '[]',
                    source_health TEXT DEFAULT '{}',
                    run_log TEXT DEFAULT '{}'
                )
            """)

            # LLM Prompt Response Cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    prompt_hash TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # LLM Usage & Token Log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    calls INTEGER DEFAULT 0,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cache_hits INTEGER DEFAULT 0,
                    estimated_cost REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL
                )
            """)

            # Concept Usage History table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS concept_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept TEXT NOT NULL,
                    used_at TEXT NOT NULL,
                    related_story TEXT
                )
            """)

            # Migrations for existing DBs
            for col, col_type in [
                ("evidence_level", "TEXT DEFAULT 'HIGH CONFIDENCE'"),
                ("is_primary_source", "INTEGER DEFAULT 0"),
                ("sources_with_urls", "TEXT DEFAULT '[]'")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE stories ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass

            for col, col_type in [
                ("what_changed", "TEXT DEFAULT '[]'"),
                ("source_health", "TEXT DEFAULT '{}'"),
                ("run_log", "TEXT DEFAULT '{}'")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE editions ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass

            conn.commit()

    # --- Cache Methods ---
    def get_cached_llm_response(self, prompt_hash: str) -> Optional[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT response FROM llm_cache WHERE prompt_hash = ?", (prompt_hash,))
            row = cursor.fetchone()
            return row["response"] if row else None

    def save_llm_cache(self, prompt_hash: str, prompt: str, response: str, model: str) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO llm_cache (prompt_hash, prompt, response, model, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (prompt_hash, prompt[:1000], response, model))
            conn.commit()

    # --- Usage Log Methods ---
    def log_llm_usage(self, log: LLMUsageLog) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO llm_usage_logs (date, calls, input_tokens, output_tokens, cache_hits, estimated_cost, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (log.date, log.calls, log.input_tokens, log.output_tokens, log.cache_hits, log.estimated_cost))
            conn.commit()

    # --- Concept History Methods ---
    def record_concept_used(self, concept: str, related_story: str = "") -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO concept_history (concept, used_at, related_story)
                VALUES (?, datetime('now'), ?)
            """, (concept, related_story))
            conn.commit()

    def get_recent_used_concepts(self, days: int = 30) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT concept FROM concept_history
                WHERE datetime(used_at) >= datetime('now', '-' || ? || ' days')
            """, (days,))
            rows = cursor.fetchall()
            return [r["concept"] for r in rows]

    # --- Standard CRUD Methods ---
    def save_article(self, article: Article) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO articles (
                        id, title, description, content, url, source, author,
                        published_at, category, sector, image_url, topics, hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article.id,
                    article.title,
                    article.description,
                    article.content,
                    article.url,
                    article.source,
                    article.author,
                    article.published_at,
                    article.category,
                    article.sector,
                    article.image_url,
                    json.dumps(article.topics),
                    article.hash,
                    article.created_at
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def save_articles(self, articles: List[Article]) -> int:
        saved_count = 0
        for article in articles:
            if self.save_article(article):
                saved_count += 1
        return saved_count

    def save_story(self, story: Story) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO stories (
                        id, headline, summary, why_it_matters, category, sector,
                        importance_score, relevance_score, final_score,
                        sources, sources_with_urls, topics, matched_watchlist,
                        evidence_level, is_primary_source, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    story.id,
                    story.headline,
                    story.summary,
                    story.why_it_matters,
                    story.category,
                    story.sector,
                    story.importance_score,
                    story.relevance_score,
                    story.final_score,
                    json.dumps(story.sources),
                    json.dumps(story.sources_with_urls),
                    json.dumps(story.topics),
                    json.dumps(story.matched_watchlist),
                    story.evidence_level,
                    1 if story.is_primary_source else 0,
                    story.created_at
                ))

                for article in story.articles:
                    self.save_article(article)
                    cursor.execute("""
                        INSERT OR IGNORE INTO article_stories (story_id, article_id)
                        VALUES (?, ?)
                    """, (story.id, article.id))

                conn.commit()
                return True
            except Exception:
                return False

    def save_edition(self, edition: Edition) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO editions (
                        edition_id, date, generated_at, html_path, pdf_path, status, stories_count,
                        what_changed, source_health, run_log
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    edition.edition_id,
                    edition.date,
                    edition.generated_at,
                    edition.html_path,
                    edition.pdf_path,
                    edition.status,
                    edition.stories_count,
                    json.dumps(edition.what_changed),
                    json.dumps(edition.source_health),
                    json.dumps(edition.run_log)
                ))
                conn.commit()
                return True
            except Exception:
                return False

    def get_recent_articles(self, limit: int = 100) -> List[Article]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM articles ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

            articles = []
            for row in rows:
                articles.append(Article(
                    id=row["id"],
                    title=row["title"],
                    description=row["description"] or "",
                    content=row["content"] or "",
                    url=row["url"],
                    source=row["source"],
                    author=row["author"] or "",
                    published_at=row["published_at"] or "",
                    category=row["category"] or "general",
                    sector=row["sector"] if "sector" in row.keys() and row["sector"] else "General",
                    image_url=row["image_url"],
                    topics=json.loads(row["topics"]) if row["topics"] else [],
                    hash=row["hash"],
                    created_at=row["created_at"]
                ))
            return articles

    def get_recent_stories(self, limit: int = 50) -> List[Story]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stories ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            stories = []
            for r in rows:
                stories.append(Story(
                    id=r["id"],
                    headline=r["headline"],
                    summary=r["summary"] or "",
                    why_it_matters=r["why_it_matters"] or "",
                    category=r["category"] or "top_stories",
                    sector=r["sector"] or "General",
                    importance_score=r["importance_score"] or 0.0,
                    relevance_score=r["relevance_score"] or 0.0,
                    final_score=r["final_score"] or 0.0,
                    sources=json.loads(r["sources"]) if r["sources"] else [],
                    sources_with_urls=json.loads(r["sources_with_urls"]) if "sources_with_urls" in r.keys() and r["sources_with_urls"] else [],
                    topics=json.loads(r["topics"]) if r["topics"] else [],
                    matched_watchlist=json.loads(r["matched_watchlist"]) if r["matched_watchlist"] else [],
                    evidence_level=r["evidence_level"] if "evidence_level" in r.keys() and r["evidence_level"] else "HIGH CONFIDENCE",
                    is_primary_source=bool(r["is_primary_source"]) if "is_primary_source" in r.keys() else False,
                    created_at=r["created_at"]
                ))
            return stories

    def get_edition_stories(self, edition_id: str = "") -> List[Story]:
        return self.get_recent_stories(limit=30)

    def get_editions(self, limit: int = 10) -> List[Edition]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM editions ORDER BY generated_at DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [
                Edition(
                    edition_id=r["edition_id"],
                    date=r["date"],
                    generated_at=r["generated_at"],
                    html_path=r["html_path"],
                    pdf_path=r["pdf_path"] if "pdf_path" in r.keys() and r["pdf_path"] else "",
                    status=r["status"],
                    stories_count=r["stories_count"],
                    what_changed=json.loads(r["what_changed"]) if "what_changed" in r.keys() and r["what_changed"] else [],
                    source_health=json.loads(r["source_health"]) if "source_health" in r.keys() and r["source_health"] else {},
                    run_log=json.loads(r["run_log"]) if "run_log" in r.keys() and r["run_log"] else {}
                ) for r in rows
            ]

    def get_latest_edition(self) -> Optional[Edition]:
        editions = self.get_editions(limit=1)
        return editions[0] if editions else None

