"""Long-running Telegram Tech News Bot with topics, dedupe, and AI summaries."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import time

from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from dedupe import DedupeStore
from formatter import (
    format_article,
    format_digest_body,
    format_digest_header,
    format_footer,
    format_search_results,
)
from news_fetcher import NewsFetcher
from summarizer import Summarizer
from topics import DEFAULT_TOPIC, TOPICS, get_topic, list_topics_help

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
POST_HOUR = int(os.getenv("POST_HOUR", "9"))
POST_MINUTE = int(os.getenv("POST_MINUTE", "0"))
ARTICLE_COUNT = int(os.getenv("ARTICLE_COUNT", "5"))
DIGEST_MODE = os.getenv("DIGEST_MODE", "1").strip().lower() not in {"0", "false", "no"}
DEFAULT_POST_TOPIC = os.getenv("DEFAULT_TOPIC", DEFAULT_TOPIC).strip().lower() or DEFAULT_TOPIC
DEDUPE_PATH = os.getenv("DEDUPE_PATH", "data/posted_urls.json")
TEST_INTERVAL_MINUTES = float(os.getenv("TEST_INTERVAL_MINUTES", "0"))
# Render Web Service sets PORT + RENDER_EXTERNAL_URL. Force with USE_WEBHOOK=1.
PORT = int(os.getenv("PORT", "8080"))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "telegram").strip().strip("/") or "telegram"

# Comma-separated Telegram user IDs allowed to trigger channel posts.
# Empty = allow anyone who can message the bot (dev-friendly default).
_admin_raw = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = {int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()}


def _use_webhook() -> bool:
    flag = os.getenv("USE_WEBHOOK", "").strip().lower()
    if flag in {"1", "true", "yes"}:
        return True
    if flag in {"0", "false", "no"}:
        return False
    return bool(os.getenv("RENDER_EXTERNAL_URL"))


def _public_base_url() -> str:
    base = (
        os.getenv("WEBHOOK_URL")
        or os.getenv("RENDER_EXTERNAL_URL")
        or ""
    ).strip().rstrip("/")
    if not base:
        raise ValueError(
            "Webhook mode needs WEBHOOK_URL or RENDER_EXTERNAL_URL "
            "(Render sets RENDER_EXTERNAL_URL automatically on Web Services)."
        )
    return base

fetcher = NewsFetcher(NEWS_API_KEY or "")
summarizer = Summarizer()
dedupe = DedupeStore(DEDUPE_PATH)


def _is_admin(update: Update) -> bool:
    if not ADMIN_IDS:
        return True
    user = update.effective_user
    return bool(user and user.id in ADMIN_IDS)


async def _deny_if_not_admin(update: Update) -> bool:
    if _is_admin(update):
        return False
    if update.message:
        await update.message.reply_text("⛔ Only bot admins can post to the channel.")
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Tech News Bot is running!\n\n"
        "Commands:\n"
        "/news – Post default tech briefing\n"
        "/search <query> – Search by custom keyword phrase\n"
        "/topics – List topic digests\n"
        "/ai /cyber /startups /cloud /gadgets – Topic digests\n"
        "/status – Bot status\n"
        "/help – Help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Tech News Bot Help*\n\n"
        "Posts curated tech briefings to your channel. Supports topic filters, "
        "duplicate skipping, custom keyword searches, and optional AI one-line summaries.\n\n"
        "*Commands:*\n"
        "/news – Post the default topic now\n"
        "/search <query> – Search and post stories for a custom phrase\n"
        "/topics – Show all topics\n"
        f"{list_topics_help()}\n"
        "/status – Scheduler + dedupe status\n\n"
        "*Env tips:*\n"
        "`ADMIN_IDS` – restrict posting\n"
        "`OPENAI_API_KEY` – enable AI summaries\n"
        "`DIGEST_MODE=1` – one briefing message\n"
        "`DIGEST_MODE=0` – one message per article",
        parse_mode="Markdown",
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.get_jobs_by_name("daily_news") if context.job_queue else []
    scheduler_status = "✅ Running" if jobs else "❌ Not scheduled"
    ai_status = "✅ On" if summarizer.available else "⏸ Off (set OPENAI_API_KEY)"
    admin_status = f"{len(ADMIN_IDS)} id(s)" if ADMIN_IDS else "open (no ADMIN_IDS)"
    await update.message.reply_text(
        f"🤖 Bot Status: ✅ Online\n"
        f"📅 Daily Scheduler: {scheduler_status}\n"
        f"🕐 Post Time: {POST_HOUR:02d}:{POST_MINUTE:02d} UTC\n"
        f"📢 Channel: {CHANNEL_ID}\n"
        f"🗂 Default topic: {DEFAULT_POST_TOPIC}\n"
        f"🧾 Digest mode: {'on' if DIGEST_MODE else 'per-article'}\n"
        f"🧠 AI summaries: {ai_status}\n"
        f"🧹 Dedupe entries: {dedupe.count()}\n"
        f"🔐 Admins: {admin_status}"
    )


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Available topics*\n\n"
        f"{list_topics_help()}\n\n"
        "Example: `/ai` posts an AI briefing to the channel.",
        parse_mode="Markdown",
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _deny_if_not_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /search <keyword or phrase>\nExample: /search AI safety")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"⏳ Searching for *{query}*...", parse_mode="Markdown")
    posted = await send_custom_news(context, query)
    if posted:
        await update.message.reply_text(f"✅ Posted {posted} new stor{'y' if posted == 1 else 'ies'} for your search.")
    else:
        await update.message.reply_text("ℹ️ Nothing new to post for that search query.")


async def post_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _deny_if_not_admin(update):
        return
    topic_key = DEFAULT_POST_TOPIC
    if context.args:
        topic_key = context.args[0].lower().strip()
    await update.message.reply_text(f"⏳ Fetching *{get_topic(topic_key).title}* news...", parse_mode="Markdown")
    posted = await send_news(context, topic_key=topic_key)
    if posted:
        await update.message.reply_text(f"✅ Posted {posted} new stor{'y' if posted == 1 else 'ies'}.")
    else:
        await update.message.reply_text("ℹ️ Nothing new to post (all stories were duplicates or fetch failed).")


def _make_topic_handler(topic_key: str):
    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if await _deny_if_not_admin(update):
            return
        topic = get_topic(topic_key)
        await update.message.reply_text(f"⏳ Fetching {topic.emoji} *{topic.title}*...", parse_mode="Markdown")
        posted = await send_news(context, topic_key=topic_key)
        if posted:
            await update.message.reply_text(f"✅ Posted {posted} {topic.title} stor{'y' if posted == 1 else 'ies'}.")
        else:
            await update.message.reply_text("ℹ️ Nothing new to post for that topic.")

    return _handler


async def send_daily_news(context: ContextTypes.DEFAULT_TYPE):
    await send_news(context, topic_key=DEFAULT_POST_TOPIC)


async def send_custom_news(context: ContextTypes.DEFAULT_TYPE, query: str, count: int = ARTICLE_COUNT) -> int:
    bot: Bot = context.bot
    raw = fetcher.get_custom_news(query, count=count, fetch_pool=count * 4)
    fresh = dedupe.filter_new(raw)[:count]

    if not fresh:
        logger.warning("No new articles for custom query=%s.", query)
        return 0

    articles = summarizer.enrich(fresh)
    body = format_search_results(articles, query)
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
            text=f"🔍 *Custom search: {query}*\n_{len(articles)} stories found_",
            parse_mode="Markdown",
        )
        for i, article in enumerate(articles, 1):
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=format_article(i, article),
                parse_mode="Markdown",
                disable_web_page_preview=False,
            )
            await asyncio.sleep(1.2)

    dedupe.mark_many(articles)
    logger.info("Posted %s articles for custom query=%s.", len(articles), query)
    return len(articles)


async def send_news(context: ContextTypes.DEFAULT_TYPE, topic_key: str = DEFAULT_TOPIC) -> int:
    bot: Bot = context.bot
    topic = get_topic(topic_key)
    raw = fetcher.get_top_tech_news(count=ARTICLE_COUNT, topic=topic, fetch_pool=ARTICLE_COUNT * 4)
    fresh = dedupe.filter_new(raw)[:ARTICLE_COUNT]

    if not fresh:
        logger.warning("No new articles for topic=%s.", topic.key)
        return 0

    articles = summarizer.enrich(fresh)

    if DIGEST_MODE:
        body = format_digest_body(articles, topic)
        # Telegram hard limit ~4096; split if needed
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

    dedupe.mark_many(articles)
    logger.info("Posted %s articles for topic=%s.", len(articles), topic.key)
    return len(articles)


def _build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("topics", topics_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("news", post_news_command))
    for key in TOPICS:
        app.add_handler(CommandHandler(key, _make_topic_handler(key)))
    _schedule_jobs(app)
    return app


def _schedule_jobs(app: Application) -> None:
    if TEST_INTERVAL_MINUTES > 0:
        app.job_queue.run_repeating(
            send_daily_news,
            interval=TEST_INTERVAL_MINUTES * 60,
            first=10,
            name="daily_news",
        )
        logger.info(
            "TEST MODE: news every %s minute(s).",
            TEST_INTERVAL_MINUTES,
        )
        return

    app.job_queue.run_daily(
        send_daily_news,
        time=time(hour=POST_HOUR, minute=POST_MINUTE),
        name="daily_news",
    )
    logger.info(
        "Daily %s briefing at %02d:%02d UTC.",
        DEFAULT_POST_TOPIC,
        POST_HOUR,
        POST_MINUTE,
    )


async def _run_webhook(app: Application) -> None:
    """HTTP server for Render Web Services: /healthz + Telegram webhook."""
    from aiohttp import web

    base = _public_base_url()
    webhook_url = f"{base}/{WEBHOOK_PATH}"

    await app.initialize()
    await app.start()
    await app.bot.set_webhook(
        url=webhook_url,
        allowed_updates=["message"],
        drop_pending_updates=True,
    )
    logger.info("Webhook set to %s", webhook_url)

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    async def telegram_webhook(request: web.Request) -> web.Response:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        if update:
            await app.process_update(update)
        return web.Response(text="OK")

    web_app = web.Application()
    web_app.router.add_get("/", health)
    web_app.router.add_get("/healthz", health)
    web_app.router.add_post(f"/{WEBHOOK_PATH}", telegram_webhook)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Listening on 0.0.0.0:%s (healthz + webhook)", PORT)

    stop = asyncio.Event()
    await stop.wait()


def main():
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")
    if not CHANNEL_ID:
        raise ValueError("TELEGRAM_CHANNEL_ID environment variable is not set.")
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY environment variable is not set.")
    if DEFAULT_POST_TOPIC not in TOPICS:
        raise ValueError(f"DEFAULT_TOPIC must be one of: {', '.join(TOPICS)}")

    app = _build_app()

    if _use_webhook():
        logger.info("Starting in webhook mode (Render Web Service).")
        asyncio.run(_run_webhook(app))
        return

    logger.info("Starting in polling mode.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
