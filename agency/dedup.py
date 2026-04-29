# -*- coding: utf-8 -*-
"""
Topic Deduplication — SQLite-based tracking.
Prevents the same news from generating posts every single run.
"""

import os
import sqlite3
import time
from agency.logger import get_logger

log = get_logger("dedup")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agency_data.db")


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection, creating the table if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_topics (
            title_hash TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            score REAL,
            processed_at REAL NOT NULL,
            approved INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at REAL NOT NULL,
            topics_fetched INTEGER DEFAULT 0,
            topics_qualified INTEGER DEFAULT 0,
            posts_generated INTEGER DEFAULT 0,
            approval_status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    return conn


def is_duplicate(title: str) -> bool:
    """Check if a topic title has been processed before."""
    title_hash = str(hash(title.strip().lower()))
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM processed_topics WHERE title_hash = ?",
            (title_hash,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def mark_processed(title: str, score: float = 0.0, approved: bool = False):
    """Mark a topic as processed to prevent future duplicates."""
    title_hash = str(hash(title.strip().lower()))
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO processed_topics (title_hash, title, score, processed_at, approved) VALUES (?, ?, ?, ?, ?)",
            (title_hash, title, score, time.time(), 1 if approved else 0)
        )
        conn.commit()
        log.debug(f"Marked topic as processed: {title[:50]}...")
    finally:
        conn.close()


def log_pipeline_run(topics_fetched: int, topics_qualified: int, posts_generated: int, approval_status: str) -> int:
    """Log a pipeline run for analytics. Returns the run ID."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO pipeline_runs (started_at, topics_fetched, topics_qualified, posts_generated, approval_status) VALUES (?, ?, ?, ?, ?)",
            (time.time(), topics_fetched, topics_qualified, posts_generated, approval_status)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_stats() -> dict:
    """Get pipeline statistics."""
    conn = _get_conn()
    try:
        total_topics = conn.execute("SELECT COUNT(*) FROM processed_topics").fetchone()[0]
        approved_topics = conn.execute("SELECT COUNT(*) FROM processed_topics WHERE approved = 1").fetchone()[0]
        total_runs = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        return {
            "total_topics_processed": total_topics,
            "total_approved": approved_topics,
            "total_pipeline_runs": total_runs,
            "approval_rate": f"{(approved_topics / total_topics * 100):.1f}%" if total_topics > 0 else "N/A"
        }
    finally:
        conn.close()
