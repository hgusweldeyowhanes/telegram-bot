import os
import asyncio
import logging
from datetime import time
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from news_fetcher import NewsFetcher

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # e.g. "@yourchannel" or "-100xxxxxxxxxx"
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
POST_HOUR = int(os.getenv("POST_HOUR", "9"))    # 9 AM by default
POST_MINUTE = int(os.getenv("POST_MINUTE", "0"))
# Set > 0 to post repeatedly on this interval (in minutes) for testing,
# starting ~10s after launch. Leave at 0 for normal once-daily posting.
TEST_INTERVAL_MINUTES = float(os.getenv("TEST_INTERVAL_MINUTES", "0"))

fetcher = NewsFetcher(NEWS_API_KEY)


# ── Commands ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Tech News Bot is running!\n\n"
        "Commands:\n"
        "/start   – Show this message\n"
        "/news    – Post latest tech news now\n"
        "/status  – Check bot status\n"
        "/help    – Help"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Tech News Bot Help*\n\n"
        "This bot automatically posts daily tech news to your Telegram channel.\n\n"
        "*Commands:*\n"
        "/news   – Fetch and post tech news immediately\n"
        "/status – Check if the bot and scheduler are running\n\n"
        "*Setup:*\n"
        "Set these environment variables:\n"
        "`TELEGRAM_BOT_TOKEN` – Your bot token from @BotFather\n"
        "`TELEGRAM_CHANNEL_ID` – Your channel ID or username\n"
        "`NEWS_API_KEY` – Your key from newsapi.org\n"
        "`POST_HOUR` – Hour to post daily (0-23, default 9)\n"
        "`POST_MINUTE` – Minute to post (0-59, default 0)",
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.get_jobs_by_name("daily_news")
    scheduler_status = "✅ Running" if jobs else "❌ Not scheduled"
    await update.message.reply_text(
        f"🤖 Bot Status: ✅ Online\n"
        f"📅 Daily Scheduler: {scheduler_status}\n"
        f"🕐 Post Time: {POST_HOUR:02d}:{POST_MINUTE:02d} UTC\n"
        f"📢 Channel: {CHANNEL_ID}"
    )

async def post_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching latest tech news...")
    await send_daily_news(context)
    await update.message.reply_text("✅ News posted successfully!")


# ── Scheduler job ─────────────────────────────────────────────────────────────

async def send_daily_news(context: ContextTypes.DEFAULT_TYPE):
    bot: Bot = context.bot
    articles = fetcher.get_top_tech_news(count=5)

    if not articles:
        logger.warning("No articles fetched.")
        return

    # Header
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    header = f"📰 *Daily Tech News – {today}*\n{'─' * 32}\n\n"
    await bot.send_message(chat_id=CHANNEL_ID, text=header, parse_mode="Markdown")

    # Articles
    for i, article in enumerate(articles, 1):
        msg = format_article(i, article)
        await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown",
                               disable_web_page_preview=False)
        await asyncio.sleep(1.5)  # avoid hitting rate limits

    # Footer
    footer = "─" * 32 + "\n🔔 Follow us for daily tech updates!"
    await bot.send_message(chat_id=CHANNEL_ID, text=footer)
    logger.info("Daily news posted successfully.")


def format_article(index: int, article: dict) -> str:
    title = article.get("title", "No title")
    description = article.get("description") or "No description available."
    url = article.get("url", "")
    source = article.get("source", {}).get("name", "Unknown")
    published = article.get("publishedAt", "")[:10]  # YYYY-MM-DD

    # Truncate long descriptions
    if len(description) > 300:
        description = description[:297] + "..."

    return (
        f"*{index}. {title}*\n\n"
        f"{description}\n\n"
        f"📌 Source: {source}  |  🗓 {published}\n"
        f"🔗 [Read more]({url})"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")
    if not CHANNEL_ID:
        raise ValueError("TELEGRAM_CHANNEL_ID environment variable is not set.")
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY environment variable is not set.")

    app = Application.builder().token(BOT_TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("news", post_news_command))

    # Schedule news posting
    if TEST_INTERVAL_MINUTES > 0:
        interval_seconds = TEST_INTERVAL_MINUTES * 60
        app.job_queue.run_repeating(
            send_daily_news,
            interval=interval_seconds,
            first=10,  # first post 10s after launch
            name="daily_news"
        )
        logger.info(
            f"Bot started in TEST MODE. News will post every "
            f"{TEST_INTERVAL_MINUTES} minute(s), starting in 10s."
        )
    else:
        app.job_queue.run_daily(
            send_daily_news,
            time=time(hour=POST_HOUR, minute=POST_MINUTE),
            name="daily_news"
        )
        logger.info(f"Bot started. Daily news will post at {POST_HOUR:02d}:{POST_MINUTE:02d} UTC.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
