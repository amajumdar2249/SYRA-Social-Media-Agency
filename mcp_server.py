# -*- coding: utf-8 -*-
"""
MCP Server v6.1 — Production-Grade
====================================
Thin wrapper exposing the agency package as MCP tools.
All logic lives in the agency/ modules.

Run: python mcp_server.py
"""

import sys
import json
import time
from mcp.server.fastmcp import FastMCP

from agency.logger import get_logger
from agency.config import VOICE, NICHE_KEYWORDS, RSS_FEEDS, MIN_VIRALITY_SCORE, PIPELINE_COOLDOWN_MIN
from agency.llm_engine import call_llm, get_engine_status
from agency.scraper import fetch_all_news
from agency.generator import filter_and_score, generate_posts
from agency.telegram import send_post, send_approval_buttons, wait_for_approval
from agency.dedup import mark_processed, log_pipeline_run, get_stats

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

log = get_logger("mcp_server")

# ============================================================
# MCP SERVER
# ============================================================
mcp = FastMCP("Social Media Agency")

# Rate limiting — track last pipeline run
_last_pipeline_run = 0.0


# ============================================================
# MCP RESOURCES
# ============================================================
@mcp.resource("config://voice-dna")
def get_voice_dna() -> str:
    """The calibrated Voice DNA framework used for post generation."""
    return VOICE

@mcp.resource("config://niche-keywords")
def get_niche_keywords() -> str:
    """Niche keywords the agency monitors for trending content."""
    return json.dumps(NICHE_KEYWORDS, indent=2)

@mcp.resource("config://rss-feeds")
def get_rss_feeds() -> str:
    """RSS feed URLs the agency scrapes for news."""
    return json.dumps(RSS_FEEDS, indent=2)


# ============================================================
# TOOL 1: get_trending_topics
# ============================================================
@mcp.tool()
def get_trending_topics(max_per_feed: int = 3, min_score: float = MIN_VIRALITY_SCORE) -> str:
    """
    Fetch trending news from RSS feeds, filter for niche relevance,
    and score them for viral potential. Automatically deduplicates
    against previously processed topics.

    Args:
        max_per_feed: Maximum news items to fetch per RSS feed (default: 3)
        min_score: Minimum virality score (1-10) to include (default: 7.5)

    Returns:
        JSON with scored, filtered trending topics.
    """
    log.info("Tool called: get_trending_topics")

    topics = fetch_all_news(max_per_feed=max_per_feed)
    if not topics:
        return json.dumps({"status": "error", "message": "No news found from any feed."})

    scored = filter_and_score(topics, min_score=min_score)

    return json.dumps({
        "status": "success",
        "total_fetched": len(topics),
        "total_qualified": len(scored),
        "min_score_used": min_score,
        "topics": scored
    }, indent=2)


# ============================================================
# TOOL 2: draft_agency_posts
# ============================================================
@mcp.tool()
def draft_agency_posts(topic_title: str, topic_summary: str) -> str:
    """
    Generate 4 viral-angle LinkedIn posts for a given topic.
    Angles: Insider Truth, Story That Teaches, Contrarian Take, Witty Observer.

    Args:
        topic_title: The headline of the trending topic
        topic_summary: A brief summary or context

    Returns:
        JSON with 4 generated posts, each labeled by angle.
    """
    log.info(f"Tool called: draft_agency_posts for '{topic_title[:50]}...'")

    posts = generate_posts(topic_title, topic_summary)

    return json.dumps({
        "status": "success",
        "topic": topic_title,
        "total_posts": len(posts),
        "posts": posts
    }, indent=2)


# ============================================================
# TOOL 3: request_human_approval
# ============================================================
@mcp.tool()
def request_human_approval_tool(
    topic: str,
    posts_json: str,
    timeout_minutes: int = 60
) -> str:
    """
    Send generated posts to Telegram with inline approval buttons,
    then wait for the human to approve one or reject all.
    Includes auth guard — only the authorized user can approve.

    Args:
        topic: The topic title (shown in Telegram header)
        posts_json: JSON string of posts (from draft_agency_posts)
        timeout_minutes: How long to wait for approval (default: 60)

    Returns:
        JSON with the approval result and the selected post text.
    """
    log.info(f"Tool called: request_human_approval for '{topic[:50]}...'")

    # Parse posts
    try:
        posts_data = json.loads(posts_json)
        posts = posts_data.get("posts", []) if isinstance(posts_data, dict) else posts_data
    except (json.JSONDecodeError, AttributeError):
        return json.dumps({"status": "error", "message": "Invalid posts_json format."})

    if not posts:
        return json.dumps({"status": "error", "message": "No posts provided."})

    # Send each post
    for p in posts:
        send_post(p.get("post_number", 0), p.get("angle", ""), topic, p.get("text", ""))
        time.sleep(0.5)

    # Send buttons
    if not send_approval_buttons(topic, len(posts)):
        return json.dumps({"status": "error", "message": "Failed to send Telegram buttons."})

    # Wait for approval (with auth guard)
    selected = wait_for_approval(timeout_minutes=timeout_minutes)

    if selected and selected > 0:
        chosen = next((p for p in posts if p.get("post_number") == selected), None)
        mark_processed(topic, approved=True)
        return json.dumps({
            "status": "approved",
            "selected_post_number": selected,
            "selected_angle": chosen.get("angle", "Unknown") if chosen else "Unknown",
            "selected_text": chosen.get("text", "") if chosen else "",
            "topic": topic
        }, indent=2)

    elif selected == -1:
        mark_processed(topic, approved=False)
        return json.dumps({"status": "rejected", "message": "All posts rejected.", "topic": topic}, indent=2)

    else:
        return json.dumps({"status": "timeout", "message": f"No response within {timeout_minutes} min.", "topic": topic}, indent=2)


# ============================================================
# TOOL 4: publish_to_linkedin (Placeholder)
# ============================================================
@mcp.tool()
def publish_to_linkedin(post_text: str) -> str:
    """
    Publish an approved post to LinkedIn.
    (Placeholder — LinkedIn API integration coming in Phase 3)

    Args:
        post_text: The approved post text to publish
    """
    log.info("Tool called: publish_to_linkedin (placeholder)")
    return json.dumps({
        "status": "placeholder",
        "message": "LinkedIn auto-publishing not yet integrated. Copy the approved post manually.",
        "post_preview": post_text[:200] + "..." if len(post_text) > 200 else post_text,
    }, indent=2)


# ============================================================
# TOOL 5: run_full_pipeline
# ============================================================
@mcp.tool()
def run_full_pipeline(max_per_feed: int = 3, min_score: float = MIN_VIRALITY_SCORE) -> str:
    """
    Run the complete autonomous pipeline end-to-end:
    Fetch → Filter → Score → Generate 4 posts → Telegram approval.
    Rate-limited to 1 run per 15 minutes.

    Args:
        max_per_feed: Max news items per RSS feed (default: 3)
        min_score: Minimum virality score threshold (default: 7.5)
    """
    global _last_pipeline_run

    # Rate limiting
    elapsed = time.time() - _last_pipeline_run
    if elapsed < PIPELINE_COOLDOWN_MIN * 60:
        remaining = int((PIPELINE_COOLDOWN_MIN * 60 - elapsed) / 60)
        return json.dumps({
            "status": "rate_limited",
            "message": f"Pipeline was run recently. Wait {remaining} more minutes.",
        }, indent=2)

    _last_pipeline_run = time.time()

    log.info("=" * 50)
    log.info("FULL PIPELINE START — v6.1 Production")
    log.info("=" * 50)

    # Step 1: Fetch & Score
    topics_result = get_trending_topics(max_per_feed=max_per_feed, min_score=min_score)
    topics_data = json.loads(topics_result)

    if topics_data["status"] != "success" or not topics_data.get("topics"):
        log_pipeline_run(topics_data.get("total_fetched", 0), 0, 0, "no_topics")
        return json.dumps({
            "status": "no_topics",
            "message": "No topics passed the virality threshold.",
        }, indent=2)

    # Step 2: Best topic
    best = topics_data["topics"][0]
    log.info(f"Best topic: {best['title'][:50]}... (Score: {best['score']})")

    # Step 3: Generate posts
    posts_result = draft_agency_posts(topic_title=best["title"], topic_summary=best["summary"])

    # Step 4: Approval
    approval_result = request_human_approval_tool(
        topic=best["title"], posts_json=posts_result, timeout_minutes=60
    )
    approval_data = json.loads(approval_result)

    # Log the run
    posts_data = json.loads(posts_result)
    log_pipeline_run(
        topics_data.get("total_fetched", 0),
        topics_data.get("total_qualified", 0),
        posts_data.get("total_posts", 0),
        approval_data.get("status", "unknown")
    )

    log.info(f"Pipeline complete. Result: {approval_data.get('status')}")

    return json.dumps({
        "status": "pipeline_complete",
        "topic_used": best["title"],
        "topic_score": best["score"],
        "approval_result": approval_data
    }, indent=2)


# ============================================================
# TOOL 6: get_agency_status (Health Check)
# ============================================================
@mcp.tool()
def get_agency_status() -> str:
    """
    Get the current health status of the agency.
    Shows LLM engine health, pipeline statistics, and configuration.
    """
    log.info("Tool called: get_agency_status")
    return json.dumps({
        "status": "online",
        "version": "6.1.0",
        "llm_engine": get_engine_status(),
        "pipeline_stats": get_stats(),
        "feeds_configured": len(RSS_FEEDS),
        "niche_keywords": len(NICHE_KEYWORDS),
    }, indent=2)


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    log.info("=" * 50)
    log.info("Social Media Agency — MCP Server v6.1")
    log.info("Tools: 6 | Resources: 3")
    log.info("Security: Telegram Auth Guard ACTIVE")
    log.info("Logging: Console + logs/agency.log")
    log.info("=" * 50)
    mcp.run()
