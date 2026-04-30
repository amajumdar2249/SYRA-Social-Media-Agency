# -*- coding: utf-8 -*-
"""
Hugging Face Web Server & Scheduler
====================================
Runs a FastAPI web server on port 7860 to satisfy Hugging Face Spaces requirements.
Runs the autonomous agency pipeline in the background every 4 hours using APScheduler.

Can be kept alive 24/7 for FREE using cron-job.org pinging the `/` route.
"""

import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from agency.logger import get_logger
from agency.config import MIN_VIRALITY_SCORE, MAX_PER_FEED
from agency.scraper import fetch_all_news
from agency.generator import filter_and_score, generate_posts
from agency.telegram import send_post, send_approval_buttons, wait_for_approval
from agency.dedup import mark_processed, log_pipeline_run, get_stats
from agency.llm_engine import get_engine_status

log = get_logger("scheduler")

# ============================================================
# CONFIGURATION
# ============================================================
PIPELINE_INTERVAL_HOURS = int(os.getenv("PIPELINE_INTERVAL_HOURS", "4"))
APPROVAL_TIMEOUT_MIN = int(os.getenv("APPROVAL_TIMEOUT_MIN", "60"))

# The global APScheduler instance
scheduler = BackgroundScheduler()


def run_pipeline_cycle():
    """Execute one full pipeline cycle."""
    log.info("=" * 50)
    log.info("PIPELINE CYCLE START")
    log.info(f"Interval: every {PIPELINE_INTERVAL_HOURS} hours")
    log.info("=" * 50)

    try:
        # Step 1: Check LLM health
        status = get_engine_status()
        available = sum(1 for v in status.values() if v.get("available"))
        if available == 0:
            log.error("No LLM providers available. Skipping this cycle.")
            log_pipeline_run(0, 0, 0, "no_llm")
            return

        # Step 2: Fetch news
        topics = fetch_all_news(max_per_feed=MAX_PER_FEED)
        if not topics:
            log.warning("No fresh topics found.")
            log_pipeline_run(0, 0, 0, "no_topics")
            return

        # Step 3: Filter & Score
        scored = filter_and_score(topics, min_score=MIN_VIRALITY_SCORE)
        if not scored:
            log.warning(f"No topics passed score {MIN_VIRALITY_SCORE}.")
            log_pipeline_run(len(topics), 0, 0, "below_threshold")
            return

        # Step 4: Generate
        best = scored[0]
        posts = generate_posts(best["title"], best["summary"])
        if not posts:
            log.error("Post generation failed.")
            log_pipeline_run(len(topics), len(scored), 0, "gen_failed")
            return

        # Step 5: Send to Telegram
        for p in posts:
            send_post(p["post_number"], p["angle"], best["title"], p["text"])
            time.sleep(0.5)

        if not send_approval_buttons(best["title"], len(posts)):
            log.error("Failed to send buttons.")
            log_pipeline_run(len(topics), len(scored), len(posts), "telegram_failed")
            return

        # Step 6: Wait Approval
        selected = wait_for_approval(timeout_minutes=APPROVAL_TIMEOUT_MIN)

        if selected and selected > 0:
            mark_processed(best["title"], score=best["score"], approved=True)
            log_pipeline_run(len(topics), len(scored), len(posts), "approved")
        elif selected == -1:
            mark_processed(best["title"], score=best["score"], approved=False)
            log_pipeline_run(len(topics), len(scored), len(posts), "rejected")
        else:
            mark_processed(best["title"], score=best["score"], approved=False)
            log_pipeline_run(len(topics), len(scored), len(posts), "timeout")

    except Exception as e:
        log.error(f"Pipeline crashed: {e}")
        log_pipeline_run(0, 0, 0, f"crash: {str(e)[:50]}")

    log.info("PIPELINE CYCLE COMPLETE")


# ============================================================
# FASTAPI APP
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    log.info(f"Starting APScheduler (Interval: {PIPELINE_INTERVAL_HOURS}h)...")
    
    # Add the job
    scheduler.add_job(
        run_pipeline_cycle,
        trigger=IntervalTrigger(hours=PIPELINE_INTERVAL_HOURS),
        id="pipeline_cycle",
        name="Agency Pipeline",
        max_instances=1,
        replace_existing=True,
    )
    
    # Start the scheduler
    scheduler.start()
    
    # Run the very first cycle immediately (non-blocking)
    scheduler.add_job(run_pipeline_cycle, id="initial_run", replace_existing=True)
    
    yield
    
    # --- Shutdown ---
    log.info("Shutting down APScheduler...")
    scheduler.shutdown()

app = FastAPI(title="Social Media Agency", lifespan=lifespan)

@app.get("/")
def ping_keepalive():
    """
    Endpoint for cron-job.org to ping.
    Returns a simple 200 OK HTML response.
    """
    html_content = """
    <html>
        <head><title>Agency Status</title></head>
        <body style="font-family: sans-serif; padding: 2rem; background: #1a1a1a; color: #fff;">
            <h2>🟢 AI Agency is Online</h2>
            <p>Running 24/7 via Hugging Face Spaces.</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/status")
def status_check():
    """Detailed health check for the agency."""
    return {
        "status": "online",
        "llm_engine": get_engine_status(),
        "pipeline_stats": get_stats()
    }

if __name__ == "__main__":
    import uvicorn
    # When running locally via CLI
    uvicorn.run("scheduler:app", host="0.0.0.0", port=7860, reload=False)
