# -*- coding: utf-8 -*-
"""
Post Generator — 4-angle viral post generation with Voice DNA.
"""

import re
import time
from typing import List, Dict

from agency.logger import get_logger
from agency.config import VOICE, POST_TEMPLATES, MIN_VIRALITY_SCORE
from agency.llm_engine import call_llm

log = get_logger("generator")


def is_relevant(title: str, summary: str) -> bool:
    """Check if a topic is relevant to the agency's niche using LLM."""
    response = call_llm(
        f"Is this about AI, AI business, social media marketing, "
        f"skill development, or entrepreneurship?\n"
        f"Topic: {title}\nSummary: {summary}\nAnswer ONLY YES or NO."
    )
    return "YES" in response.strip().upper()


def rate_topic(title: str, summary: str) -> float:
    """Score a topic's viral potential (1.0–10.0) using LLM."""
    response = call_llm(
        f"Rate viral potential on LinkedIn for AI/business audience. "
        f"ONLY a number 1.0-10.0.\n"
        f"Topic: {title}\nSummary: {summary}"
    )
    match = re.search(r'([0-9]+\.?[0-9]*)', response)
    score = min(float(match.group(1)), 10.0) if match else 5.0
    log.debug(f"Topic scored {score}/10: {title[:50]}...")
    return score


def filter_and_score(topics: List[Dict], min_score: float = MIN_VIRALITY_SCORE) -> List[Dict]:
    """
    Filter topics for relevance and score their viral potential.

    Args:
        topics: Raw topics from scraper
        min_score: Minimum virality score to qualify

    Returns:
        Scored and filtered topics, sorted best-first.
    """
    scored = []

    for item in topics:
        title = item["title"]
        summary = item["summary"]

        if not is_relevant(title, summary):
            log.info(f"Not relevant, skipping: {title[:50]}...")
            continue

        score = rate_topic(title, summary)
        if score >= min_score:
            scored.append({**item, "score": score})
            log.info(f"Qualified ({score}/10): {title[:50]}...")
        else:
            log.info(f"Below threshold ({score} < {min_score}): {title[:50]}...")

        time.sleep(0.5)

    scored.sort(key=lambda x: x["score"], reverse=True)
    log.info(f"{len(scored)}/{len(topics)} topics passed the {min_score} threshold")
    return scored


def generate_posts(title: str, summary: str) -> List[Dict]:
    """
    Generate 4 viral-angle LinkedIn posts for a topic.

    Angles: Insider Truth, Story That Teaches, Contrarian Take, Witty Observer

    Args:
        title: The topic headline
        summary: Topic context/summary

    Returns:
        List of dicts with post_number, angle, and text.
    """
    posts = []

    for name, template in POST_TEMPLATES:
        prompt = (
            template
            .replace("{{VOICE}}", VOICE)
            .replace("{{TOPIC}}", title)
            .replace("{{CONTEXT}}", summary)
        )

        text = call_llm(prompt)
        if text:
            posts.append({
                "post_number": len(posts) + 1,
                "angle": name,
                "text": text
            })
            log.info(f"[{name}] Generated successfully")
        else:
            posts.append({
                "post_number": len(posts) + 1,
                "angle": name,
                "text": f"[FAILED] Could not generate {name} post."
            })
            log.error(f"[{name}] Generation failed")

        time.sleep(1)

    return posts
