# 📰 Telegram Daily Tech News Bot

A bot that posts curated tech briefings to your Telegram channel — with **topic filters**, **duplicate skipping**, and optional **AI one-line summaries**.

---

## Features
- ✅ Daily scheduled briefing (or GitHub Actions one-shot)
- ✅ Topic digests: `/tech` `/ai` `/cyber` `/startups` `/cloud` `/gadgets`
- ✅ Deduplication so the same story is not posted twice
- ✅ Optional OpenAI one-line summaries (`OPENAI_API_KEY`)
- ✅ Digest mode: one clean briefing message (or classic per-article posts)
- ✅ Admin-only posting via `ADMIN_IDS`
- ✅ `/news` on demand · `/status` · `/topics` · `/help`

---

## Setup (Step-by-Step)

### 1. Create Your Telegram Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** you receive

### 2. Create a Telegram Channel
1. Create a new channel in Telegram (public or private)
2. Add your bot as an **Administrator** with permission to post messages
3. Your channel ID is either:
   - Public: `@yourchannel`
   - Private: A number like `-1001234567890`  
     (Forward a message to @userinfobot to find it)

### 3. Get a News API Key
1. Go to [https://newsapi.org/register](https://newsapi.org/register)
2. Sign up for a free account
3. Copy your API key

### 4. Install & Configure

```bash
cd telegram-bot
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your tokens
```

### 5. Run the Bot

```bash
python bot.py
```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather | `123456:ABC-DEF...` |
| `TELEGRAM_CHANNEL_ID` | Channel username or numeric ID | `@mytechchannel` |
| `NEWS_API_KEY` | API key from newsapi.org | `abc123def456` |
| `POST_HOUR` / `POST_MINUTE` | Daily post time (UTC) | `9` / `0` |
| `DEFAULT_TOPIC` | Daily topic key | `tech` |
| `ARTICLE_COUNT` | Stories per post | `5` |
| `DIGEST_MODE` | `1` = one briefing · `0` = per article | `1` |
| `ADMIN_IDS` | Comma-separated Telegram user IDs | `123456789` |
| `DEDUPE_PATH` | Fingerprint JSON path | `data/posted_urls.json` |
| `OPENAI_API_KEY` | Optional; enables AI summaries | `sk-...` |
| `OPENAI_MODEL` | Chat model for summaries | `gpt-4o-mini` |
| `AI_SUMMARY` | `0` disables AI even if key set | `1` |

---

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome |
| `/help` | Help + setup tips |
| `/status` | Scheduler, AI, dedupe, admins |
| `/topics` | List topic commands |
| `/news` | Post default topic now |
| `/news ai` | Post a topic by name |
| `/tech` `/ai` `/cyber` `/startups` `/cloud` `/gadgets` | Topic digests |

---

## How the new features work

**Topics** — each command maps to a NewsAPI keyword query (AI, cyber, startups, …).

**Dedupe** — after a successful post, article URL/title fingerprints are saved under `data/posted_urls.json`. The next run skips those URLs and pulls extras so you still get a full briefing.

**AI summaries** — if `OPENAI_API_KEY` is set, each story gets a short one-sentence blurb. Without a key, the NewsAPI description is trimmed instead (bot still works).

**Admins** — set `ADMIN_IDS` to your numeric Telegram user id(s). Only those users can trigger channel posts. Leave empty for open access while developing.

---

## Tests

```bash
python -m unittest discover -s tests -v
```

---

## Running in Production

### Option A: Deploy on Render (recommended)

The bot runs as a **Web Service** with Telegram **webhooks** (works on Render’s free web tier). Long-polling alone is better as a paid Background Worker.

#### One-click Blueprint
1. Push this repo to GitHub
2. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
3. Select the repo (uses `render.yaml`)
4. Fill secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `NEWS_API_KEY`
5. Optional: `ADMIN_IDS`, `OPENAI_API_KEY`
6. Deploy — Render sets `RENDER_EXTERNAL_URL` and `PORT` automatically

Health check: `GET /healthz` → `ok`

#### Manual Web Service
1. **New** → **Web Service** → connect repo
2. Runtime: **Python 3**
3. Build: `pip install -r requirements.txt`
4. Start: `python bot.py`
5. Instance: Free (or Starter if you want no spin-down)
6. Health Check Path: `/healthz`
7. Environment:

| Key | Value |
|-----|--------|
| `USE_WEBHOOK` | `1` |
| `TELEGRAM_BOT_TOKEN` | from BotFather |
| `TELEGRAM_CHANNEL_ID` | `@channel` or `-100…` |
| `NEWS_API_KEY` | newsapi.org |
| `DEFAULT_TOPIC` | `tech` |
| `DIGEST_MODE` | `1` |
| `POST_HOUR` / `POST_MINUTE` | UTC schedule |
| `ADMIN_IDS` | your Telegram user id (optional) |
| `OPENAI_API_KEY` | optional AI summaries |

After deploy, open `https://YOUR-APP.onrender.com/healthz` — you should see `ok`. Then message the bot `/status`.

**Free tier note:** the service may sleep when idle; the first Telegram update can be slow while it wakes. For 24/7 reliability use a **Starter** plan, or keep GitHub Actions cron (`post_news.py`) for the daily post.

#### Cron-only on Render (posts daily, no live commands)
Create a **Cron Job** service:
- Schedule: `0 9 * * *` (09:00 UTC)
- Build: `pip install -r requirements.txt`
- Command: `python post_news.py`
- Same secrets as above (`USE_WEBHOOK` not needed)

### Option B: Keep it running with `screen`
```bash
screen -S techbot
python bot.py
```

### Option C: Fly.io
See `fly.toml` — long-polling worker, no HTTP ports. Set `USE_WEBHOOK=0`.

### Option D: GitHub Actions (post once, exit)
`.github/workflows/daily-news.yml` runs `python post_news.py` on a cron.
Add secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `NEWS_API_KEY`, and optionally `OPENAI_API_KEY`.

---

## Free Tier Limits (newsapi.org)
- 100 requests/day on the free plan — plenty for a daily bot
- Topic commands also count against that quota
