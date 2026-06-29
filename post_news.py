"""Post a single batch of daily tech news, then exit.

Designed for scheduled runs (e.g. GitHub Actions cron). Unlike bot.py, this
does NOT start a long-running poller — it posts once and quits, which is all
a CI environment needs.
"""
import os
import asyncio
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from telegram import Bot

from news_fetcher import NewsFetcher

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
ARTICLE_COUNT = int(os.getenv("ARTICLE_COUNT", "5"))


def format_article(index: int, article: dict) -> str:
    title = article.get("title", "No title")
    description = article.get("description") or "No description available."
    url = article.get("url", "")
    source = article.get("source", {}).get("name", "Unknown")
    published = article.get("publishedAt", "")[:10]

    if len(description) > 300:
        description = description[:297] + "..."

    return (
        f"*{index}. {title}*\n\n"
        f"{description}\n\n"
        f"📌 Source: {source}  |  🗓 {published}\n"
        f"🔗 [Read more]({url})"
    )


async def post_once() -> None:
    missing = [
        name for name, value in {
            "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
            "TELEGRAM_CHANNEL_ID": CHANNEL_ID,
            "NEWS_API_KEY": NEWS_API_KEY,
        }.items() if not value
    ]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

    fetcher = NewsFetcher(NEWS_API_KEY)
    articles = fetcher.get_top_tech_news(count=ARTICLE_COUNT)
    if not articles:
        logger.warning("No articles fetched — nothing to post.")
        return

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    header = f"📰 *Daily Tech News – {today}*\n{'─' * 32}\n\n"

    bot = Bot(BOT_TOKEN)
    async with bot:
        await bot.send_message(chat_id=CHANNEL_ID, text=header, parse_mode="Markdown")
        for i, article in enumerate(articles, 1):
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=format_article(i, article),
                parse_mode="Markdown",
                disable_web_page_preview=False,
            )
            await asyncio.sleep(1.5)  # avoid rate limits
        footer = "─" * 32 + "\n🔔 Follow us for daily tech updates!"
        await bot.send_message(chat_id=CHANNEL_ID, text=footer)

    logger.info("Daily news posted successfully (%d articles).", len(articles))


if __name__ == "__main__":
    asyncio.run(post_once())
