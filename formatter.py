"""Shared Telegram message formatting for news digests."""
from __future__ import annotations

from datetime import datetime, timezone

from topics import Topic


def format_article(index: int, article: dict, topic: Topic | None = None) -> str:
    title = article.get("title", "No title")
    summary = article.get("summary") or article.get("description") or "No summary available."
    url = article.get("url", "")
    source = article.get("source", {}).get("name", "Unknown")
    published = (article.get("publishedAt") or "")[:10]
    emoji = topic.emoji if topic else "📌"

    if len(summary) > 300:
        summary = summary[:297] + "..."

    return (
        f"{emoji} *{index}. {title}*\n\n"
        f"{summary}\n\n"
        f"📌 Source: {source}  |  🗓 {published}\n"
        f"🔗 [Read more]({url})"
    )


def format_digest_header(topic: Topic, count: int) -> str:
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return (
        f"{topic.emoji} *{topic.title} Briefing – {today}*\n"
        f"_{count} {'story' if count == 1 else 'stories'}_\n"
        f"{'─' * 28}\n"
    )


def format_digest_body(articles: list[dict], topic: Topic) -> str:
    """Single-message briefing: numbered titles + one-line summaries."""
    lines = [format_digest_header(topic, len(articles))]
    for i, article in enumerate(articles, 1):
        title = article.get("title", "No title")
        summary = article.get("summary") or article.get("description") or ""
        url = article.get("url", "")
        source = article.get("source", {}).get("name", "Unknown")
        if len(summary) > 160:
            summary = summary[:157] + "..."
        lines.append(f"*{i}. {title}*\n{summary}\n[{source} →]({url})\n")
    lines.append("─" * 28)
    lines.append("🔔 Reply /ai /cyber /startups for topic digests.")
    return "\n".join(lines)


def format_footer(topic: Topic | None = None) -> str:
    label = topic.title if topic else "tech"
    return f"{'─' * 28}\n🔔 Follow for daily {label.lower()} updates · /topics"
