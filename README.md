# 🤖 Autonomous Social Media Agency

> An AI-powered, multi-agent automation pipeline that researches trending topics, generates viral LinkedIn content in a human voice, and delivers it via Telegram for human-in-the-loop approval.

---

## 🚀 What It Does

This is a **fully autonomous social media content engine** built for LinkedIn thought leadership. It:

1. **Monitors** real-time trending news via RSS feeds (AI, Business, Marketing, Skill Development)
2. **Filters & Scores** topics using AI relevance checks and virality scoring (1–10)
3. **Generates 4 viral-angle posts** per topic using a deeply calibrated voice framework:
   - ✦ **Insider Truth** — Reframes the news with non-obvious insights
   - ✦ **Story That Teaches** — Mid-scene narrative with a twist lesson
   - ✦ **Contrarian Take** — Bold reframe that challenges common belief
   - ✦ **Witty Observer** — Dry humor with devastating contrasts
4. **Delivers to Telegram** with inline approval buttons
5. **Waits for human approval** before proceeding — true human-in-the-loop

---

## 🧠 Architecture

```
RSS Feeds (TechCrunch, VentureBeat, Google News, AI News)
         │
         ▼
   ┌─────────────┐
   │  Core Engine │ ← Multi-LLM Engine
   │  (main.py)   │   OpenRouter (GPT-4o) → DeepSeek → Gemini
   └──────┬──────┘
          │
    ┌─────┴─────┐
    │            │
    ▼            ▼
 Filter &    Generate 4
 Score (AI)  Viral Posts
    │            │
    └─────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  Telegram    │ ← Inline Keyboard Buttons
   │  Approval    │   ✅ Publish Post 1/2/3/4
   └──────┬──────┘   ❌ Reject All
          │
          ▼
    Human Approved
    → LinkedIn Ready
```

---

## ⚡ Tech Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.10+ |
| **Primary LLM** | OpenRouter (GPT-4o) |
| **Fallback LLM 1** | DeepSeek V3 |
| **Fallback LLM 2** | Google Gemini 2.0 Flash |
| **News Source** | RSS Feeds (feedparser) |
| **Approval System** | Telegram Bot (Inline Keyboards) |
| **Deployment** | Local / Cloud (GitHub Actions) |

---

## 📦 Setup

```bash
# 1. Clone the repo
git clone https://github.com/amajumdar2249/SYRA-Social-Media-Agency.git
cd SYRA-Social-Media-Agency

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run the pipeline
python main.py
```

---

## 🔑 Required API Keys

| Service | Get Key From | Cost |
|---|---|---|
| OpenRouter | [openrouter.ai](https://openrouter.ai) | Pay-per-use (~$0.01/post) |
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com) | 5M free tokens |
| Gemini | [aistudio.google.com](https://aistudio.google.com) | Free tier |
| Telegram Bot | [@BotFather](https://t.me/BotFather) | Free |

---

## 🛣️ Roadmap

- [x] Multi-LLM Engine (OpenRouter + DeepSeek + Gemini)
- [x] 4-Angle Post Generation (Calibrated from 12 real samples)
- [x] Telegram 2-Way Approval (Inline Buttons)
- [ ] MCP Server Integration (Autonomous Agent)
- [ ] LinkedIn Auto-Posting via API
- [ ] Cloud Deployment (24/7 Autonomous)
- [ ] Advanced Data Sources (Apify, Reddit, Twitter)

---

## 👤 Author

**Aurgho Majumdar**  
Building an AI that thinks, writes, and delivers.

---

## 📄 License

This project is for educational and personal use.
