"""SQLite storage and incremental crawl helpers."""
from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = "crawl.db"


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Initialise database and return connection."""
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                status INTEGER,
                last_seen TEXT,
                last_modified TEXT,
                etag TEXT,
                content_hash TEXT,
                screenshot_hash TEXT
            )
            """
        )
    return conn


def get_page(conn: sqlite3.Connection, url: str) -> Optional[Dict[str, Any]]:
    """Return page record for *url* or ``None``."""
    cur = conn.execute(
        "SELECT url, status, last_seen, last_modified, etag, content_hash, screenshot_hash FROM pages WHERE url=?",
        (url,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    keys = [d[0] for d in cur.description]
    return dict(zip(keys, row))


def touch_page(conn: sqlite3.Connection, url: str) -> None:
    """Update ``last_seen`` for an unmodified page."""
    with conn:
        conn.execute(
            "UPDATE pages SET last_seen=? WHERE url=?",
            (datetime.utcnow().isoformat(), url),
        )


def upsert_page(
    conn: sqlite3.Connection,
    *,
    url: str,
    status: int,
    last_modified: Optional[str],
    etag: Optional[str],
    content_hash: str,
    screenshot_hash: Optional[str],
) -> None:
    """Insert or update a page record."""
    with conn:
        conn.execute(
            """
            INSERT INTO pages(url, status, last_seen, last_modified, etag, content_hash, screenshot_hash)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                status=excluded.status,
                last_seen=excluded.last_seen,
                last_modified=excluded.last_modified,
                etag=excluded.etag,
                content_hash=excluded.content_hash,
                screenshot_hash=excluded.screenshot_hash
            """,
            (
                url,
                status,
                datetime.utcnow().isoformat(),
                last_modified,
                etag,
                content_hash,
                screenshot_hash,
            ),
        )


def sha256_text(text: str) -> str:
    """Return SHA256 hash of given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
