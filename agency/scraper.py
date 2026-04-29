# -*- coding: utf-8 -*-
"""
News Scraper — RSS fetching with deduplication.
"""

import re
import feedparser
from typing import List, Dict

from agency.logger import get_logger
from agency.config import RSS_FEEDS, MAX_SUMMARY_LENGTH
from agency.dedup import is_duplicate

log = get_logger("scraper")


def fetch_all_news(max_per_feed: int = 3) -> List[Dict[str, str]]:
    """
    Fetch news from all configured RSS feeds.
    Automatically deduplicates against:
    1. Topics seen in THIS run (in-memory set)
    2. Topics processed in PREVIOUS runs (SQLite)

    Args:
        max_per_feed: Maximum items to fetch per RSS source

    Returns:
        List of dicts with title, summary, and link.
    """
    all_items = []
    seen_this_run = set()

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            fetched = 0
            for entry in feed.entries:
                if fetched >= max_per_feed:
                    break

                title = entry.get('title', '').strip()
                if not title:
                    continue

                # Skip if seen in this run
                if title in seen_this_run:
                    continue

                # Skip if processed in a previous run
                if is_duplicate(title):
                    log.debug(f"Skipping duplicate: {title[:50]}...")
                    continue

                seen_this_run.add(title)

                # Clean HTML from summary
                raw_summary = entry.get('summary', '')
                clean_summary = re.sub(r'<[^<]+?>', '', raw_summary)[:MAX_SUMMARY_LENGTH]

                all_items.append({
                    "title": title,
                    "summary": clean_summary,
                    "link": entry.get('link', '')
                })
                fetched += 1

        except Exception as e:
            log.warning(f"Failed to fetch {url}: {e}")

    log.info(f"Fetched {len(all_items)} fresh topics from {len(RSS_FEEDS)} feeds")
    return all_items
