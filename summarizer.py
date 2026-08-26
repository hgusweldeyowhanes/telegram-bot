"""Optional one-line AI summaries; falls back to cleaned descriptions."""
from __future__ import annotations

import logging
import os
import re
from typing import Iterable

import requests

logger = logging.getLogger(__name__)


def clean_description(text: str | None, limit: int = 220) -> str:
    if not text:
        return "No summary available."
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) > limit:
        return cleaned[: limit - 3] + "..."
    return cleaned


class Summarizer:
    """
    Summarize articles with OpenAI when OPENAI_API_KEY is set.
    Otherwise reuse / trim the NewsAPI description.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        enabled: bool | None = None,
    ):
        self.api_key = (api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")).strip()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if enabled is None:
            enabled = os.getenv("AI_SUMMARY", "1").strip().lower() not in {"0", "false", "no"}
        self.enabled = bool(enabled and self.api_key)

    @property
    def available(self) -> bool:
        return self.enabled

    def summarize_article(self, article: dict) -> str:
        title = article.get("title") or ""
        description = article.get("description") or ""
        if not self.enabled:
            return clean_description(description)

        prompt = (
            "Write one plain sentence (max 35 words) summarizing this tech news "
            "for a Telegram channel. No hashtags, no quotes, no preface.\n\n"
            f"Title: {title}\n"
            f"Description: {description}"
        )
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "temperature": 0.3,
                    "max_tokens": 80,
                    "messages": [
                        {"role": "system", "content": "You write concise tech news blurbs."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            return clean_description(text, limit=280)
        except Exception as e:
            logger.warning("AI summary failed, using description: %s", e)
            return clean_description(description)

    def enrich(self, articles: Iterable[dict]) -> list[dict]:
        enriched = []
        for article in articles:
            copy = dict(article)
            copy["summary"] = self.summarize_article(article)
            enriched.append(copy)
        return enriched
