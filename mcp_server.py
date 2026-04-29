# -*- coding: utf-8 -*-
"""
MCP Server — Social Media Agency v6.0
======================================
Exposes the full autonomous pipeline as MCP tools.
Any AI (Claude, Gemini, GPT) can now control this agency.

Tools:
  - get_trending_topics: Fetch, filter, and score news
  - draft_agency_posts: Generate 4 viral-angle LinkedIn posts
  - request_human_approval: Send to Telegram + wait for button click
  - publish_to_linkedin: (Placeholder) Auto-publish approved post

Resources:
  - voice_dna: The calibrated voice framework
  - niche_config: Keywords and RSS feeds

Run: python mcp_server.py
"""

import os, sys, re, time, json, feedparser, requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from google import genai
from openai import OpenAI

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

load_dotenv()

# ============================================================
# MCP SERVER INIT
# ============================================================
mcp = FastMCP("Social Media Agency")

# ============================================================
# CONFIGURATION (Niche + Voice DNA)
# ============================================================
NICHE_KEYWORDS = [
    "artificial intelligence", "AI", "machine learning", "deep learning",
    "LLM", "GPT", "generative AI", "AI startup", "AI business",
    "social media marketing", "digital marketing", "content strategy",
    "personal branding", "LinkedIn growth", "audience building",
    "skill development", "upskilling", "career growth", "tech skills",
    "automation", "AI agents", "no-code", "SaaS", "entrepreneurship",
]

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://news.google.com/rss/search?q=artificial+intelligence+business&hl=en-US&gl=US&ceid=US:en",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://www.artificialintelligence-news.com/feed/",
]

VOICE = """You replicate the founder's exact voice for LinkedIn.

WHO HE IS:
Early-stage builder. Doesn't fake success. Anti-fluff. Observational.
Quiet "watch me build" energy. Authority from clarity, not experience.

HIS BELIEFS:
- Social media is a game. Most are being played.
- I don't announce. I deliver. Then I talk.
- Nobody is coming to save you.

WRITING DNA (from 12 analyzed posts):
1. REFRAME, don't report. Never describe news. Show what people are MISSING.
2. Every insight = PAIR. A claim on one line, then a twist on the next.
   Example: "Prompting skill just lost value / The model now fills gaps you used to engineer manually"
3. Include ONE human truth per post — a line that goes DEEPER than the topic.
   Example: "They're scared of being average in a world that's accelerating"
4. Use ONE extended metaphor — visual, specific, continued across 2 lines.
   Example: "You're building on rented intelligence / And the landlord keeps upgrading the house"
5. Use the STACKING pattern: "Not X / Not Y / Just Z"
   Example: "Not hours / Not effort / Just results"
6. DEVASTATING contrasts in 2-4 words: "Proud / But unemployed", "Same people / New labels"
7. The word "quietly" is signature: "quietly rewriting expectations", "quietly fall behind"
8. Dialogue in quotes makes stories feel real: "Why does this still take you so long?"
9. Close is QUIET — a truth or calm question, never "WHAT DO YOU THINK?!"
10. Killer final lines — 3-5 word bombs: "It deletes categories", "Silence did"

STYLE:
- Short sentences dominate. 3-8 words per line.
- Blank lines between thoughts for breathing room.
- 80-130 words per post. Not less, not more.
- No emojis. No hashtags.
- Dashes for short lists (– not bullets).
- Dry humor = truth expressed simply. Never forced jokes.

NEVER USE: "In today's world", "Game-changing", "Leverage", "Synergy", "Excited to share",
"Humbled", "Let me know your thoughts", "Deep dive", "Move the needle", "At the end of the day",
"Here's my framework", "Let me explain", "Passionate", "Navigate", "Landscape", "Cutting-edge",
"Paradigm", "Unprecedented", "Revolutionary", "Comprehensive", "Staggering", "Delve"

NEVER SOUND LIKE: Guru, corporate writer, motivational speaker, news reporter, AI content
ALWAYS SOUND LIKE: Builder thinking out loud, someone who speaks less but says more
"""

# ============================================================
# 4-ANGLE POST TEMPLATES
# ============================================================
INSIDER_TRUTH_PROMPT = """{{VOICE}}

Write an INSIDER TRUTH LinkedIn post about the topic below.

REAL EXAMPLE — match this EXACT depth, rhythm, pacing, and length:
---
The OpenAI GPT-5.5 launch isn't about the model.

It's about what just became obsolete.

Here's what most people will miss:

Capability jumps kill "in-between" products
Anything slightly better than GPT-4 level just got erased
Prompting skill just lost value
The model now fills gaps you used to engineer manually
AI wrappers just got thinner
If your product = "better interface" → fragile
Expectations just reset
What felt impressive yesterday is now baseline
The gap isn't tech anymore
It's distribution + positioning + speed

Everyone's celebrating the launch

Smart ones are auditing their business

Because every major model release does one thing quietly:

It deletes categories
---

STRUCTURE:
1. Take the topic → REJECT the obvious angle in 2 lines
2. "Here's what most people will miss:" or "What nobody tells you:"
3. 4-6 paired insights (claim line + twist line)
4. Quiet close with a 3-5 word killer final line

Topic: {{TOPIC}}
Context: {{CONTEXT}}

Write ONLY the post. No labels, metadata, or explanations."""

STORY_PROMPT = """{{VOICE}}

Write a STORY THAT TEACHES LinkedIn post about the topic below.

REAL EXAMPLE — match this EXACT depth, rhythm, pacing, and length:
---
A friend of mine almost lost his job last quarter

Not because he was bad

Because he was average

His work:
– Reports
– Research
– Documentation

All things AI now does… fast

His manager didn't say it directly

But the signal was clear

"Why does this still take you so long?"

That week he changed one thing

He stopped doing work manually

Started using AI for first drafts
Spent time improving thinking instead

Within a month:
– Faster delivery
– Better ideas
– More visibility

Same role

Different leverage

That's when it clicked

AI didn't replace him

It exposed how he was working
---

STRUCTURE:
1. Start mid-scene with stakes ("almost lost", "nothing happened")
2. Specific details: numbers, timeframes, actions taken
3. Include ONE line of dialogue in quotes
4. Show contrast between two approaches or before/after
5. "That's when it clicked" → lesson as reframe, NOT a moral

Topic: {{TOPIC}}
Context: {{CONTEXT}}

Write ONLY the post. No labels, metadata, or explanations."""

CONTRARIAN_PROMPT = """{{VOICE}}

Write a CONTRARIAN TAKE LinkedIn post about the topic below.

REAL EXAMPLE — match this EXACT depth, rhythm, pacing, and length:
---
GPT-5.5 isn't scary

Your dependence on it is

Here's why:

If your advantage is:
– "Using AI"
– "Access to better models"
– "Faster output"

You don't have an advantage

You have a temporary edge

And it expires on every launch

Real leverage now is:
– Taste
– Judgment
– Distribution

The model keeps improving

So your differentiation must move

Upstream

Otherwise you're building on rented intelligence

And the landlord keeps upgrading the house

Question is:

What part of your business still works
If everyone has the same AI as you?
---

STRUCTURE:
1. Open with reframe OR common belief in quotes → "No." → reframe
2. "Here's why:" → logic in short lines
3. IF/BUT contrast with dash lists
4. ONE extended metaphor continued across 2 lines
5. Challenge close as a calm question

Topic: {{TOPIC}}
Context: {{CONTEXT}}

Write ONLY the post. No labels, metadata, or explanations."""

WITTY_PROMPT = """{{VOICE}}

Write a WITTY OBSERVER LinkedIn post about the topic below.

REAL EXAMPLE — match this EXACT depth, rhythm, pacing, and length:
---
People are scared AI will take their job

But still refuse to use it daily

Interesting strategy

It's like seeing a calculator for the first time

And deciding to double down on mental math

Proud

But unemployed

AI isn't waiting for you to be ready

It's already part of the workflow

So you can either:
Ignore it

Or quietly fall behind someone who didn't
---

STRUCTURE:
1. Dry observation about absurd behavior (not a joke)
2. "Which is funny" or "Interesting strategy" — dry commentary
3. ONE visual metaphor that's slightly funny
4. 2-4 word devastating contrast ("Proud / But unemployed")
5. Sharp truth landing — calm, not aggressive

Keep this the SHORTEST post. Under 90 words ideally.

Topic: {{TOPIC}}
Context: {{CONTEXT}}

Write ONLY the post. No labels, metadata, or explanations."""


# ============================================================
# API CLIENTS (Initialized once at server start)
# ============================================================
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
) if os.getenv("OPENROUTER_API_KEY") else None

deepseek_client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY")
) if os.getenv("DEEPSEEK_API_KEY") else None

gemini_clients = []
for key in [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2"), os.getenv("GEMINI_API_KEY_3")]:
    if key:
        gemini_clients.append(genai.Client(api_key=key))

telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{telegram_token}" if telegram_token else ""


# ============================================================
# MULTI-LLM ENGINE (Internal — used by tools)
# ============================================================
def call_llm(prompt: str) -> str:
    """3-tier fallback: OpenRouter (GPT-4o) -> DeepSeek -> Gemini."""

    # 1. OpenRouter (GPT-4o)
    if openrouter_client:
        try:
            c = openrouter_client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=800,
            )
            return c.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [FALLBACK] OpenRouter failed ({e}), trying DeepSeek...")

    # 2. DeepSeek
    if deepseek_client:
        try:
            c = deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=800,
            )
            return c.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [FALLBACK] DeepSeek failed ({e}), trying Gemini...")

    # 3. Gemini Fallback
    for i, client in enumerate(gemini_clients):
        try:
            r = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return r.text.strip()
        except Exception as e:
            print(f"  [FALLBACK] Gemini key {i+1} failed, trying next...")

    return "[ERROR] All LLMs failed."


# ============================================================
# MCP RESOURCES — Expose config to any connected AI
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
# MCP TOOL 1: get_trending_topics
# ============================================================
@mcp.tool()
def get_trending_topics(max_per_feed: int = 3, min_score: float = 7.5) -> str:
    """
    Fetch trending news from RSS feeds, filter for niche relevance,
    and score them for viral potential.

    Args:
        max_per_feed: Maximum news items to fetch per RSS feed (default: 3)
        min_score: Minimum virality score (1-10) to include (default: 7.5)

    Returns:
        JSON string with scored, filtered trending topics ready for post generation.
    """
    print("\n📡 [MCP] get_trending_topics called")

    # Fetch from all RSS feeds
    all_items, seen = [], set()
    for url in RSS_FEEDS:
        try:
            for e in feedparser.parse(url).entries[:max_per_feed]:
                t = e.get('title', '')
                if t and t not in seen:
                    seen.add(t)
                    s = re.sub('<[^<]+?>', '', e.get('summary', ''))[:400]
                    all_items.append({"title": t, "summary": s, "link": e.get('link', '')})
        except Exception:
            pass

    if not all_items:
        return json.dumps({"status": "error", "message": "No news found from any feed."})

    print(f"  Found {len(all_items)} raw topics. Filtering & scoring...")

    # Filter for relevance + score
    scored = []
    for item in all_items:
        # Relevance check
        r = call_llm(
            f"Is this about AI, AI business, social media marketing, skill development, or entrepreneurship?\n"
            f"Topic: {item['title']}\nSummary: {item['summary']}\nAnswer ONLY YES or NO."
        )
        if "YES" not in r.strip().upper():
            continue

        # Score virality
        t = call_llm(
            f"Rate viral potential on LinkedIn for AI/business audience. "
            f"ONLY a number 1.0-10.0.\nTopic: {item['title']}\nSummary: {item['summary']}"
        )
        m = re.search(r'([0-9]+\.?[0-9]*)', t)
        score = min(float(m.group(1)), 10.0) if m else 5.0

        if score >= min_score:
            scored.append({**item, "score": score})

        time.sleep(0.5)

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    print(f"  ✅ {len(scored)} topics passed the {min_score} threshold.")

    return json.dumps({
        "status": "success",
        "total_fetched": len(all_items),
        "total_qualified": len(scored),
        "min_score_used": min_score,
        "topics": scored
    }, indent=2)


# ============================================================
# MCP TOOL 2: draft_agency_posts
# ============================================================
@mcp.tool()
def draft_agency_posts(topic_title: str, topic_summary: str) -> str:
    """
    Generate 4 viral-angle LinkedIn posts for a given topic using
    the calibrated voice framework.

    The 4 angles are:
    1. Insider Truth — Reframes news with non-obvious insights
    2. Story That Teaches — Mid-scene narrative with a twist lesson
    3. Contrarian Take — Bold reframe challenging common beliefs
    4. Witty Observer — Dry humor with devastating contrasts

    Args:
        topic_title: The headline/title of the trending topic
        topic_summary: A brief summary or context of the topic

    Returns:
        JSON string with 4 generated posts, each labeled by angle.
    """
    print(f"\n✍️ [MCP] draft_agency_posts called for: {topic_title[:50]}...")

    templates = [
        ("INSIDER TRUTH", INSIDER_TRUTH_PROMPT),
        ("STORY THAT TEACHES", STORY_PROMPT),
        ("CONTRARIAN TAKE", CONTRARIAN_PROMPT),
        ("WITTY OBSERVER", WITTY_PROMPT),
    ]

    posts = []
    for name, template in templates:
        prompt = (
            template
            .replace("{{VOICE}}", VOICE)
            .replace("{{TOPIC}}", topic_title)
            .replace("{{CONTEXT}}", topic_summary)
        )
        text = call_llm(prompt)
        if text and "[ERROR]" not in text:
            posts.append({"post_number": len(posts) + 1, "angle": name, "text": text})
            print(f"    [{name}] ✅ Done.")
        else:
            posts.append({"post_number": len(posts) + 1, "angle": name, "text": f"[FAILED] Could not generate {name} post."})
            print(f"    [{name}] ❌ Failed.")
        time.sleep(1)

    return json.dumps({
        "status": "success",
        "topic": topic_title,
        "total_posts": len(posts),
        "posts": posts
    }, indent=2)


# ============================================================
# MCP TOOL 3: request_human_approval
# ============================================================
@mcp.tool()
def request_human_approval(
    topic: str,
    posts_json: str,
    timeout_minutes: int = 60
) -> str:
    """
    Send generated posts to Telegram with inline approval buttons,
    then wait for the human to approve one or reject all.

    Args:
        topic: The topic title (shown in Telegram header)
        posts_json: JSON string of posts array (from draft_agency_posts)
        timeout_minutes: How long to wait for approval (default: 60)

    Returns:
        JSON string with the approval result and the selected post text.
    """
    print(f"\n📱 [MCP] request_human_approval called for: {topic[:50]}...")

    if not telegram_token or not telegram_chat_id:
        return json.dumps({"status": "error", "message": "Telegram credentials not configured."})

    # Parse the posts
    try:
        posts_data = json.loads(posts_json)
        if isinstance(posts_data, dict):
            posts = posts_data.get("posts", [])
        else:
            posts = posts_data
    except json.JSONDecodeError:
        return json.dumps({"status": "error", "message": "Invalid posts_json format."})

    if not posts:
        return json.dumps({"status": "error", "message": "No posts provided."})

    # Send each post as a separate message with ✦ headers
    for p in posts:
        pnum = p.get("post_number", "?")
        angle = p.get("angle", "Unknown")
        text = p.get("text", "")

        msg = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"TOPIC: {topic}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✦ POST {pnum} — {angle}\n"
            f"─────────────────────────────\n"
            f"{text}"
        )
        try:
            requests.post(f"{TELEGRAM_API}/sendMessage",
                         json={"chat_id": telegram_chat_id, "text": msg[:4096]})
        except Exception:
            pass
        time.sleep(0.5)

    # Send approval buttons
    buttons = []
    for p in posts:
        pnum = p.get("post_number", 0)
        buttons.append([{"text": f"✅ Publish Post {pnum}", "callback_data": f"publish_{pnum}"}])
    buttons.append([{"text": "❌ Reject All — Regenerate", "callback_data": "reject_all"}])

    approval_msg = (
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
        requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": telegram_chat_id,
            "text": approval_msg,
            "reply_markup": {"inline_keyboard": buttons}
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to send Telegram buttons: {e}"})

    print(f"  ⏳ Waiting for approval (timeout: {timeout_minutes} min)...")

    # Poll for button click
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
                if callback:
                    cb_data = callback.get("data", "")
                    cb_id = callback.get("id")

                    # Acknowledge the button press
                    requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={
                        "callback_query_id": cb_id,
                        "text": "✅ Received!"
                    })

                    if cb_data.startswith("publish_"):
                        post_num = int(cb_data.split("_")[1])
                        chosen_post = next((p for p in posts if p.get("post_number") == post_num), None)

                        requests.post(f"{TELEGRAM_API}/sendMessage", json={
                            "chat_id": telegram_chat_id,
                            "text": f"✅ Post {post_num} APPROVED!\n\n📋 Copy the post above and publish it on LinkedIn.\n\n— AI Agency Pipeline"
                        })

                        return json.dumps({
                            "status": "approved",
                            "selected_post_number": post_num,
                            "selected_angle": chosen_post.get("angle", "Unknown") if chosen_post else "Unknown",
                            "selected_text": chosen_post.get("text", "") if chosen_post else "",
                            "topic": topic
                        }, indent=2)

                    elif cb_data == "reject_all":
                        requests.post(f"{TELEGRAM_API}/sendMessage", json={
                            "chat_id": telegram_chat_id,
                            "text": "❌ All posts rejected. Pipeline will regenerate on next cycle.\n\n— AI Agency Pipeline"
                        })

                        return json.dumps({
                            "status": "rejected",
                            "message": "All posts rejected by user.",
                            "topic": topic
                        }, indent=2)

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"  [POLLING ERROR] {e}")
            time.sleep(5)

    return json.dumps({
        "status": "timeout",
        "message": f"No response received within {timeout_minutes} minutes.",
        "topic": topic
    }, indent=2)


# ============================================================
# MCP TOOL 4: publish_to_linkedin (Placeholder)
# ============================================================
@mcp.tool()
def publish_to_linkedin(post_text: str) -> str:
    """
    Publish an approved post to LinkedIn.
    (Currently a placeholder — LinkedIn API integration coming in Phase 3)

    Args:
        post_text: The final approved post text to publish

    Returns:
        JSON string with the publish status.
    """
    print(f"\n🔗 [MCP] publish_to_linkedin called (placeholder)")

    # Placeholder — In Phase 3, this will use LinkedIn's OAuth2 API
    return json.dumps({
        "status": "placeholder",
        "message": "LinkedIn auto-publishing not yet integrated. Please copy the approved post manually.",
        "post_preview": post_text[:200] + "..." if len(post_text) > 200 else post_text,
        "next_step": "Phase 3 will integrate LinkedIn's Official Publishing API."
    }, indent=2)


# ============================================================
# MCP TOOL 5: run_full_pipeline (Convenience orchestrator)
# ============================================================
@mcp.tool()
def run_full_pipeline(max_per_feed: int = 3, min_score: float = 7.5) -> str:
    """
    Run the complete autonomous pipeline end-to-end:
    Fetch news → Filter → Score → Generate 4 posts → Telegram approval.

    This is a convenience tool that chains all other tools together.

    Args:
        max_per_feed: Max news items per RSS feed (default: 3)
        min_score: Minimum virality score threshold (default: 7.5)

    Returns:
        JSON string with the full pipeline result.
    """
    print("\n" + "=" * 55)
    print("  AI AGENCY PIPELINE v6.0 — MCP Server Mode")
    print("  Niche: AI | Business | Marketing | Skills")
    print("  Engine: OpenRouter (GPT-4o) → DeepSeek → Gemini")
    print("  Approval: 2-Way Telegram (Inline Buttons)")
    print("=" * 55)

    # Step 1: Get trending topics
    topics_result = get_trending_topics(max_per_feed=max_per_feed, min_score=min_score)
    topics_data = json.loads(topics_result)

    if topics_data["status"] != "success" or not topics_data.get("topics"):
        return json.dumps({
            "status": "no_topics",
            "message": "No topics passed the virality threshold. Try again later.",
            "details": topics_data
        }, indent=2)

    # Step 2: Pick the best topic
    best = topics_data["topics"][0]
    print(f"\n  🏆 BEST TOPIC: {best['title'][:50]}... (Score: {best['score']})")

    # Step 3: Generate 4 posts
    posts_result = draft_agency_posts(
        topic_title=best["title"],
        topic_summary=best["summary"]
    )

    # Step 4: Send to Telegram for approval
    approval_result = request_human_approval(
        topic=best["title"],
        posts_json=posts_result,
        timeout_minutes=60
    )
    approval_data = json.loads(approval_result)

    return json.dumps({
        "status": "pipeline_complete",
        "topic_used": best["title"],
        "topic_score": best["score"],
        "approval_result": approval_data
    }, indent=2)


# ============================================================
# SERVER ENTRY POINT
# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("  🚀 Social Media Agency — MCP Server v6.0")
    print("  Tools: get_trending_topics, draft_agency_posts,")
    print("         request_human_approval, publish_to_linkedin,")
    print("         run_full_pipeline")
    print("  Resources: voice-dna, niche-keywords, rss-feeds")
    print("=" * 55)
    print("\n  Starting MCP server on stdio transport...\n")
    mcp.run()
