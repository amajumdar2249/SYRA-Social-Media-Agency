# -*- coding: utf-8 -*-
"""
Social Media Automation Pipeline v5.0
==========================================
Aurgho Majumdar's Voice Engine — 4-Angle LinkedIn Post Generator.
Now with 2-Way Telegram Approval (Inline Buttons).

Engine: OpenRouter (GPT-4o) -> DeepSeek -> Gemini (Fallback)
"""

# ============================================================
# NICHE KEYWORDS
# ============================================================
NICHE_KEYWORDS = [
    "artificial intelligence", "AI", "machine learning", "deep learning",
    "LLM", "GPT", "generative AI", "AI startup", "AI business",
    "social media marketing", "digital marketing", "content strategy",
    "personal branding", "LinkedIn growth", "audience building",
    "skill development", "upskilling", "career growth", "tech skills",
    "automation", "AI agents", "no-code", "SaaS", "entrepreneurship",
]

# ============================================================
# AURGHO'S VOICE DNA (Calibrated from 12 sample posts)
# ============================================================
VOICE = """You replicate Aurgho Majumdar's exact voice for LinkedIn.

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

# RSS feeds (AI, Business, Marketing)
RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://news.google.com/rss/search?q=artificial+intelligence+business&hl=en-US&gl=US&ceid=US:en",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://www.artificialintelligence-news.com/feed/",
]

import os, sys, io, re, time, json, feedparser, requests
from dotenv import load_dotenv
from google import genai
from openai import OpenAI

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
load_dotenv()

# ============================================================
# API CLIENTS
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

# ============================================================
# MULTI-LLM ENGINE
# ============================================================
def call_llm(prompt: str) -> str:
    """Tries OpenRouter (GPT-4o), then DeepSeek, then Gemini keys."""
    
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

    # 2. DeepSeek (deepseek-chat)
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
            
    print("  [ERROR] All LLMs failed.")
    return ""

# ============================================================
# NEWS + FILTERING
# ============================================================
def fetch_all_news(max_per_feed=3):
    all_items, seen = [], set()
    for url in RSS_FEEDS:
        try:
            for e in feedparser.parse(url).entries[:max_per_feed]:
                t = e.get('title','')
                if t and t not in seen:
                    seen.add(t)
                    s = re.sub('<[^<]+?>', '', e.get('summary',''))[:400]
                    all_items.append({"title": t, "summary": s, "link": e.get('link','')})
        except: pass
    return all_items

def is_relevant(title, summary):
    r = call_llm(f"Is this about AI, AI business, social media marketing, skill development, or entrepreneurship?\nTopic: {title}\nSummary: {summary}\nAnswer ONLY YES or NO.")
    return "YES" in r.strip().upper()

def rate_topic(title, summary):
    t = call_llm(f"Rate viral potential on LinkedIn for AI/business audience. ONLY a number 1.0-10.0.\nTopic: {title}\nSummary: {summary}")
    m = re.search(r'([0-9]+\.?[0-9]*)', t)
    return min(float(m.group(1)), 10.0) if m else 5.0

# ============================================================
# 4-ANGLE POST GENERATION (Calibrated from 12 samples)
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

def generate_4_posts(title, summary):
    """Generates 4 posts using Aurgho's calibrated framework."""
    posts = []
    templates = [
        ("INSIDER TRUTH", INSIDER_TRUTH_PROMPT),
        ("STORY THAT TEACHES", STORY_PROMPT),
        ("CONTRARIAN TAKE", CONTRARIAN_PROMPT),
        ("WITTY OBSERVER", WITTY_PROMPT),
    ]
    for name, template in templates:
        prompt = template.replace("{{VOICE}}", VOICE).replace("{{TOPIC}}", title).replace("{{CONTEXT}}", summary)
        text = call_llm(prompt)
        if text:
            posts.append({"angle": name, "text": text})
            print(f"    [{name}] Done.")
        time.sleep(1)
    return posts

# ============================================================
# TELEGRAM (2-WAY APPROVAL WITH INLINE BUTTONS)
# ============================================================
TELEGRAM_API = f"https://api.telegram.org/bot{telegram_token}"

def send_telegram_post(post_num, angle, topic, score, post_text):
    """Send a single post to Telegram with proper ✦ header formatting."""
    if not telegram_token or not telegram_chat_id:
        return False
    
    msg = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"TOPIC: {topic}\n"
        f"SCORE: {score}/10\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✦ POST {post_num} — {angle}\n"
        f"─────────────────────────────\n"
        f"{post_text}"
    )
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage",
                         json={"chat_id": telegram_chat_id, "text": msg[:4096]})
        return r.status_code == 200
    except:
        return False

def send_approval_buttons(topic, num_posts):
    """Send inline keyboard buttons for post selection."""
    if not telegram_token or not telegram_chat_id:
        return None
    
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
            "chat_id": telegram_chat_id,
            "text": msg,
            "reply_markup": {"inline_keyboard": buttons}
        })
        return r.json() if r.status_code == 200 else None
    except:
        return None

def wait_for_approval(timeout_minutes=60):
    """Poll Telegram for the user's button click. Returns selected post number or None."""
    print(f"\n  ⏳ Waiting for your approval on Telegram (timeout: {timeout_minutes} min)...")
    
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
                        # Send confirmation message
                        requests.post(f"{TELEGRAM_API}/sendMessage", json={
                            "chat_id": telegram_chat_id,
                            "text": f"✅ Post {post_num} APPROVED!\n\n📋 Copy the post above and publish it on LinkedIn.\n\n— AI Agency Pipeline"
                        })
                        return post_num
                    
                    elif cb_data == "reject_all":
                        requests.post(f"{TELEGRAM_API}/sendMessage", json={
                            "chat_id": telegram_chat_id,
                            "text": "❌ All posts rejected. Pipeline will regenerate on next cycle.\n\n— AI Agency Pipeline"
                        })
                        return -1
        
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"  [POLLING ERROR] {e}")
            time.sleep(5)
    
    print("  ⏰ Approval timed out.")
    return None

# ============================================================
# MAIN PIPELINE
# ============================================================
def run_pipeline():
    print("=" * 55)
    print("  AI AGENCY PIPELINE v5.0 — Voice Engine")
    print("  Niche: AI | Business | Marketing | Skills")
    print("  Engine: OpenRouter (GPT-4o) → DeepSeek → Gemini")
    print("  Approval: 2-Way Telegram (Inline Buttons)")
    print("=" * 55)
    
    # ---- STEP 1: Fetch News ----
    print("\n[1/6] Fetching news...")
    news = fetch_all_news(max_per_feed=3)
    if not news:
        print("  No news found.")
        return
    print(f"  Found {len(news)} topics.\n")
    
    # ---- STEP 2: Filter & Score ----
    scored = []
    for i, item in enumerate(news):
        print(f"[2/6] Checking {i+1}/{len(news)}: {item['title'][:55]}...")
        if not is_relevant(item['title'], item['summary']):
            print(f"  Skipped.\n")
            continue
        print(f"  Relevant! Rating...")
        score = rate_topic(item['title'], item['summary'])
        print(f"  Score: {score}/10\n")
        if score >= 7.5:
            scored.append({**item, "score": score})
        time.sleep(1)
    
    if not scored:
        print("No topics passed the 7.5 threshold. Retry next cycle.")
        return
    
    # ---- STEP 3: Pick Best Topic ----
    best = max(scored, key=lambda x: x["score"])
    print("=" * 55)
    print(f"  BEST TOPIC: {best['title'][:50]}...")
    print(f"  SCORE: {best['score']}/10")
    print("=" * 55)
    
    # ---- STEP 4: Generate 4 Posts ----
    print("\n[4/6] Writing 4 viral angle posts...")
    posts = generate_4_posts(best['title'], best['summary'])
    if not posts:
        print("  Failed to generate posts.")
        return
    
    # ---- STEP 5: Send to Telegram with Headers ----
    print(f"\n[5/6] Sending {len(posts)} posts to Telegram...\n")
    for i, p in enumerate(posts):
        post_num = i + 1
        print(f"  Sending ✦ POST {post_num} — {p['angle']}...")
        if send_telegram_post(post_num, p['angle'], best['title'], best['score'], p['text']):
            print(f"  [TELEGRAM] ✦ POST {post_num} — {p['angle']} sent!")
        time.sleep(1)
    
    # ---- STEP 6: Send Approval Buttons & Wait ----
    print(f"\n[6/6] Sending approval buttons...")
    result = send_approval_buttons(best['title'], len(posts))
    if not result:
        print("  Failed to send approval buttons.")
        return
    
    print("  ✅ Buttons sent to Telegram!")
    
    # Wait for user's button click
    selected = wait_for_approval(timeout_minutes=60)
    
    if selected and selected > 0:
        chosen = posts[selected - 1]
        print(f"\n{'='*55}")
        print(f"  ✅ POST {selected} — {chosen['angle']} APPROVED!")
        print(f"{'='*55}")
        print(chosen['text'])
        print(f"\n[DONE] Post {selected} approved. Ready for LinkedIn.")
    elif selected == -1:
        print("\n  ❌ All posts rejected by user. Will regenerate next cycle.")
    else:
        print("\n  ⏰ No response received within timeout.")

if __name__ == "__main__":
    run_pipeline()
