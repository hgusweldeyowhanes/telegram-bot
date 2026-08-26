"""Post a single batch of tech news, then exit (GitHub Actions / cron)."""
from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Bot

from dedupe import DedupeStore
from formatter import format_article, format_digest_body, format_digest_header, format_footer
from news_fetcher import NewsFetcher
from summarizer import Summarizer
from topics import DEFAULT_TOPIC, TOPICS, get_topic

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
DIGEST_MODE = os.getenv("DIGEST_MODE", "1").strip().lower() not in {"0", "false", "no"}
TOPIC_KEY = os.getenv("DEFAULT_TOPIC", DEFAULT_TOPIC).strip().lower() or DEFAULT_TOPIC
DEDUPE_PATH = os.getenv("DEDUPE_PATH", "data/posted_urls.json")


async def post_once() -> None:
    missing = [
        name
        for name, value in {
            "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
            "TELEGRAM_CHANNEL_ID": CHANNEL_ID,
            "NEWS_API_KEY": NEWS_API_KEY,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
    if TOPIC_KEY not in TOPICS:
        raise SystemExit(f"DEFAULT_TOPIC must be one of: {', '.join(TOPICS)}")

    topic = get_topic(TOPIC_KEY)
    fetcher = NewsFetcher(NEWS_API_KEY)
    summarizer = Summarizer()
    store = DedupeStore(DEDUPE_PATH)

    raw = fetcher.get_top_tech_news(count=ARTICLE_COUNT, topic=topic, fetch_pool=ARTICLE_COUNT * 4)
    fresh = store.filter_new(raw)[:ARTICLE_COUNT]
    if not fresh:
        logger.warning("No new articles for topic=%s — nothing to post.", topic.key)
        return

    articles = summarizer.enrich(fresh)
    bot = Bot(BOT_TOKEN)
    async with bot:
        if DIGEST_MODE:
            body = format_digest_body(articles, topic)
            if len(body) <= 4000:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=body,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
            else:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=format_digest_header(topic, len(articles)),
                    parse_mode="Markdown",
                )
                for i, article in enumerate(articles, 1):
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=format_article(i, article, topic),
                        parse_mode="Markdown",
                        disable_web_page_preview=False,
                    )
                    await asyncio.sleep(1.2)
                await bot.send_message(chat_id=CHANNEL_ID, text=format_footer(topic))
        else:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=format_digest_header(topic, len(articles)),
                parse_mode="Markdown",
            )
            for i, article in enumerate(articles, 1):
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=format_article(i, article, topic),
                    parse_mode="Markdown",
                    disable_web_page_preview=False,
                )
                await asyncio.sleep(1.5)
            await bot.send_message(chat_id=CHANNEL_ID, text=format_footer(topic))

    store.mark_many(articles)
    logger.info("Posted %s articles for topic=%s.", len(articles), topic.key)


if __name__ == "__main__":
    asyncio.run(post_once())
