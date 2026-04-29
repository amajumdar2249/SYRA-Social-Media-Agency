# -*- coding: utf-8 -*-
"""
Telegram Module — 2-Way Approval System with Auth Guard.

Security: Verifies that button clicks come from the authorized user only.
No unauthorized person can approve posts even if they discover the bot.
"""

import os
import time
import requests
from typing import Optional, List, Dict
from dotenv import load_dotenv

from agency.logger import get_logger
from agency.config import TELEGRAM_MSG_LIMIT, APPROVAL_TIMEOUT_MIN

load_dotenv()
log = get_logger("telegram")

# ============================================================
# CONFIGURATION
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else ""

# Auth guard — only this user ID can interact with the bot
AUTHORIZED_USER_ID = int(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else None


def _is_configured() -> bool:
    """Check if Telegram credentials are set."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("Telegram credentials not configured in .env")
        return False
    return True


def _is_authorized(user_id: int) -> bool:
    """
    AUTH GUARD — Verify the button click came from the authorized user.
    Prevents unauthorized approvals even if someone discovers the bot.
    """
    if AUTHORIZED_USER_ID is None:
        return False
    authorized = (user_id == AUTHORIZED_USER_ID)
    if not authorized:
        log.warning(f"Unauthorized access attempt from user_id: {user_id}")
    return authorized


def send_post(post_num: int, angle: str, topic: str, post_text: str) -> bool:
    """Send a single formatted post to Telegram."""
    if not _is_configured():
        return False

    msg = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"TOPIC: {topic}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✦ POST {post_num} — {angle}\n"
        f"─────────────────────────────\n"
        f"{post_text}"
    )

    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg[:TELEGRAM_MSG_LIMIT]},
            timeout=10
        )
        if r.status_code == 200:
            log.info(f"Sent POST {post_num} ({angle}) to Telegram")
            return True
        else:
            log.error(f"Telegram API error {r.status_code}: {r.text[:200]}")
            return False
    except requests.RequestException as e:
        log.error(f"Telegram send failed: {e}")
        return False


def send_approval_buttons(topic: str, num_posts: int) -> bool:
    """Send inline keyboard buttons for post selection."""
    if not _is_configured():
        return False

    buttons = []
    for i in range(1, num_posts + 1):
        buttons.append([{"text": f"✅ Publish Post {i}", "callback_data": f"publish_{i}"}])
    buttons.append([{"text": "❌ Reject All — Regenerate", "callback_data": "reject_all"}])

    msg = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 APPROVAL REQUIRED\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Topic: {topic}\n\n"
        "📌 Screenshot Test: Would someone screenshot this post?\n"
        "If YES → Tap the button below to approve.\n"
        "If NO → Tap Reject to regenerate.\n\n"
        "👇 Select which post to publish on LinkedIn:"
    )

    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "reply_markup": {"inline_keyboard": buttons}
        }, timeout=10)
        if r.status_code == 200:
            log.info("Approval buttons sent to Telegram")
            return True
        else:
            log.error(f"Failed to send buttons: {r.text[:200]}")
            return False
    except requests.RequestException as e:
        log.error(f"Failed to send buttons: {e}")
        return False


def wait_for_approval(timeout_minutes: int = APPROVAL_TIMEOUT_MIN) -> Optional[int]:
    """
    Poll Telegram for button click. Returns:
    - Positive int: Selected post number
    - -1: All rejected
    - None: Timeout

    SECURITY: Only responds to clicks from the authorized user.
    """
    if not _is_configured():
        return None

    log.info(f"Waiting for approval (timeout: {timeout_minutes} min)...")

    last_update_id = None
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    while (time.time() - start_time) < timeout_seconds:
        try:
            params = {"timeout": 30}
            if last_update_id:
                params["offset"] = last_update_id + 1

            r = requests.get(f"{TELEGRAM_API}/getUpdates", params=params, timeout=35)
            data = r.json()

            if not data.get("ok"):
                time.sleep(5)
                continue

            for update in data.get("result", []):
                last_update_id = update["update_id"]

                callback = update.get("callback_query")
                if not callback:
                    continue

                # AUTH GUARD — Verify user identity
                from_user = callback.get("from", {})
                user_id = from_user.get("id")

                if not _is_authorized(user_id):
                    # Silently ignore unauthorized clicks
                    requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={
                        "callback_query_id": callback.get("id"),
                        "text": "⛔ Unauthorized. Access denied."
                    })
                    continue

                cb_data = callback.get("data", "")
                cb_id = callback.get("id")

                # Acknowledge the button press
                requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={
                    "callback_query_id": cb_id,
                    "text": "✅ Received!"
                })

                if cb_data.startswith("publish_"):
                    post_num = int(cb_data.split("_")[1])
                    requests.post(f"{TELEGRAM_API}/sendMessage", json={
                        "chat_id": TELEGRAM_CHAT_ID,
                        "text": f"✅ Post {post_num} APPROVED!\n\n📋 Copy the post above and publish it on LinkedIn.\n\n— AI Agency Pipeline"
                    })
                    log.info(f"Post {post_num} APPROVED by user {user_id}")
                    return post_num

                elif cb_data == "reject_all":
                    requests.post(f"{TELEGRAM_API}/sendMessage", json={
                        "chat_id": TELEGRAM_CHAT_ID,
                        "text": "❌ All posts rejected. Pipeline will regenerate on next cycle.\n\n— AI Agency Pipeline"
                    })
                    log.info(f"All posts REJECTED by user {user_id}")
                    return -1

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            log.error(f"Polling error: {e}")
            time.sleep(5)

    log.warning("Approval timed out")
    return None
