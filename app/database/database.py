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
                    topics TEXT,
                    matched_watchlist TEXT,
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
                    stories_count INTEGER DEFAULT 0
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
                        sources, topics, matched_watchlist, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps(story.topics),
                    json.dumps(story.matched_watchlist),
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
                        edition_id, date, generated_at, html_path, pdf_path, status, stories_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    edition.edition_id,
                    edition.date,
                    edition.generated_at,
                    edition.html_path,
                    edition.pdf_path,
                    edition.status,
                    edition.stories_count
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
                    stories_count=r["stories_count"]
                ) for r in rows
            ]
