# -*- coding: utf-8 -*-
"""
Scheduler — Autonomous Pipeline Runner
========================================
Runs the full agency pipeline on a fixed schedule (default: every 4 hours).
Designed for cloud deployment (GCP, Render, Railway, etc.)

Features:
  - APScheduler with configurable interval
  - Graceful shutdown on SIGTERM/SIGINT
  - Health heartbeat logging
  - Crash recovery (auto-restarts pipeline on failure)

Run locally:  python scheduler.py
Run on VM:    nohup python scheduler.py &
"""

import os
import sys
import signal
import time

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from agency.logger import get_logger
from agency.config import MIN_VIRALITY_SCORE, MAX_PER_FEED
from agency.scraper import fetch_all_news
from agency.generator import filter_and_score, generate_posts
from agency.telegram import send_post, send_approval_buttons, wait_for_approval
from agency.dedup import mark_processed, log_pipeline_run
from agency.llm_engine import get_engine_status

log = get_logger("scheduler")

# ============================================================
# CONFIGURATION
# ============================================================
PIPELINE_INTERVAL_HOURS = int(os.getenv("PIPELINE_INTERVAL_HOURS", "4"))
APPROVAL_TIMEOUT_MIN = int(os.getenv("APPROVAL_TIMEOUT_MIN", "60"))


def run_pipeline_cycle():
    """
    Execute one full pipeline cycle:
    Fetch → Filter → Score → Generate → Telegram → Wait for Approval
    """
    log.info("=" * 50)
    log.info("PIPELINE CYCLE START")
    log.info(f"Interval: every {PIPELINE_INTERVAL_HOURS} hours")
    log.info("=" * 50)

    try:
        # Step 1: Check LLM engine health
        status = get_engine_status()
        available = sum(1 for v in status.values() if v.get("available"))
        if available == 0:
            log.error("No LLM providers available. Skipping this cycle.")
            log_pipeline_run(0, 0, 0, "no_llm")
            return

        log.info(f"LLM engines online: {available}/3")

        # Step 2: Fetch news
        log.info("[1/5] Fetching trending topics...")
        topics = fetch_all_news(max_per_feed=MAX_PER_FEED)
        if not topics:
            log.warning("No fresh topics found. Skipping cycle.")
            log_pipeline_run(0, 0, 0, "no_topics")
            return

        log.info(f"Found {len(topics)} fresh topics")

        # Step 3: Filter & Score
        log.info("[2/5] Filtering and scoring...")
        scored = filter_and_score(topics, min_score=MIN_VIRALITY_SCORE)
        if not scored:
            log.warning(f"No topics passed the {MIN_VIRALITY_SCORE} threshold. Skipping.")
            log_pipeline_run(len(topics), 0, 0, "below_threshold")
            return

        # Step 4: Generate posts for best topic
        best = scored[0]
        log.info(f"[3/5] Best topic: {best['title'][:50]}... (Score: {best['score']})")
        log.info("Generating 4 viral-angle posts...")
        posts = generate_posts(best["title"], best["summary"])

        if not posts:
            log.error("Post generation failed. Skipping cycle.")
            log_pipeline_run(len(topics), len(scored), 0, "gen_failed")
            return

        log.info(f"Generated {len(posts)} posts")

        # Step 5: Send to Telegram
        log.info("[4/5] Sending posts to Telegram...")
        for p in posts:
            send_post(p["post_number"], p["angle"], best["title"], p["text"])
            time.sleep(0.5)

        if not send_approval_buttons(best["title"], len(posts)):
            log.error("Failed to send approval buttons")
            log_pipeline_run(len(topics), len(scored), len(posts), "telegram_failed")
            return

        # Step 6: Wait for approval
        log.info(f"[5/5] Waiting for approval (timeout: {APPROVAL_TIMEOUT_MIN} min)...")
        selected = wait_for_approval(timeout_minutes=APPROVAL_TIMEOUT_MIN)

        if selected and selected > 0:
            chosen = posts[selected - 1]
            log.info(f"POST {selected} ({chosen['angle']}) APPROVED!")
            mark_processed(best["title"], score=best["score"], approved=True)
            log_pipeline_run(len(topics), len(scored), len(posts), "approved")

        elif selected == -1:
            log.info("All posts REJECTED by user")
            mark_processed(best["title"], score=best["score"], approved=False)
            log_pipeline_run(len(topics), len(scored), len(posts), "rejected")

        else:
            log.warning("Approval TIMED OUT")
            mark_processed(best["title"], score=best["score"], approved=False)
            log_pipeline_run(len(topics), len(scored), len(posts), "timeout")

    except Exception as e:
        log.error(f"Pipeline cycle CRASHED: {e}", exc_info=True)
        log_pipeline_run(0, 0, 0, f"crash: {str(e)[:100]}")

    log.info("=" * 50)
    log.info("PIPELINE CYCLE COMPLETE")
    log.info(f"Next run in {PIPELINE_INTERVAL_HOURS} hours")
    log.info("=" * 50)


def main():
    """Start the autonomous scheduler."""
    log.info("=" * 55)
    log.info("  SOCIAL MEDIA AGENCY — AUTONOMOUS SCHEDULER")
    log.info(f"  Version: 6.1.0")
    log.info(f"  Schedule: Every {PIPELINE_INTERVAL_HOURS} hours")
    log.info(f"  Approval timeout: {APPROVAL_TIMEOUT_MIN} min")
    log.info("=" * 55)

    # Run first cycle immediately
    log.info("Running first cycle immediately...")
    run_pipeline_cycle()

    # Schedule recurring runs
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_pipeline_cycle,
        trigger=IntervalTrigger(hours=PIPELINE_INTERVAL_HOURS),
        id="pipeline_cycle",
        name="Agency Pipeline Cycle",
        max_instances=1,                # Prevent overlapping runs
        replace_existing=True,
        misfire_grace_time=3600,         # Allow 1 hour grace if a cycle is missed
    )

    # Graceful shutdown
    def shutdown(signum, frame):
        log.info("Shutdown signal received. Stopping scheduler...")
        scheduler.shutdown(wait=False)
        log.info("Scheduler stopped. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log.info(f"Scheduler started. Next cycle in {PIPELINE_INTERVAL_HOURS} hours.")
    log.info("Press Ctrl+C to stop.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
