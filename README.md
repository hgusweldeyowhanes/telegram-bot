# 📰 Telegram Daily Tech News Bot

A bot that automatically posts top tech news to your Telegram channel every day.

---

## Features
- ✅ Posts 5 top tech articles daily at a scheduled time
- ✅ `/news` command to post instantly on demand
- ✅ `/status` command to check scheduler status
- ✅ Fallback keyword search if category headlines are unavailable
- ✅ Clean formatted messages with source, date, and link

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
# Clone or download this project
cd telegram-tech-bot

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your actual values
nano .env
```

### 5. Run the Bot

```bash
python bot.py
```

---

## Environment Variables

| Variable              | Description                              | Example                  |
|-----------------------|------------------------------------------|--------------------------|
| `TELEGRAM_BOT_TOKEN`  | Token from @BotFather                    | `123456:ABC-DEF...`      |
| `TELEGRAM_CHANNEL_ID` | Channel username or numeric ID           | `@mytechchannel`         |
| `NEWS_API_KEY`        | API key from newsapi.org                 | `abc123def456`           |
| `POST_HOUR`           | Hour to post daily (UTC, 0–23)           | `9`                      |
| `POST_MINUTE`         | Minute to post (0–59)                    | `0`                      |

---

## Commands

| Command   | Description                        |
|-----------|------------------------------------|
| `/start`  | Show welcome message               |
| `/news`   | Post tech news immediately         |
| `/status` | Check bot and scheduler status     |
| `/help`   | Show help and setup info           |

---

## Running in Production

### Option A: Keep it running with `screen`
```bash
screen -S techbot
python bot.py
# Press Ctrl+A then D to detach
```

### Option B: systemd service (Linux)
```ini
# /etc/systemd/system/techbot.service
[Unit]
Description=Telegram Tech News Bot
After=network.target

[Service]
WorkingDirectory=/path/to/telegram-tech-bot
EnvironmentFile=/path/to/telegram-tech-bot/.env
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable techbot
sudo systemctl start techbot
```

### Option C: Deploy on a free cloud server
- **Railway** – [railway.app](https://railway.app) (free tier)
- **Render** – [render.com](https://render.com) (free tier)
- **Fly.io** – [fly.io](https://fly.io) (free tier)

---

## Free Tier Limits (newsapi.org)
- 100 requests/day on the free plan — plenty for a daily bot
- For heavy usage, upgrade to a paid plan
