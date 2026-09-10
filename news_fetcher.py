"""Fetch tech headlines from NewsAPI, optionally filtered by topic."""
from __future__ import annotations

import logging
from typing import Dict, List

import requests

from topics import DEFAULT_TOPIC, Topic, get_topic

logger = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"
EVERYTHING_URL = "https://newsapi.org/v2/everything"


class NewsFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-Api-Key": api_key})

    def get_custom_news(
        self,
        query: str,
        count: int = 5,
        fetch_pool: int | None = None,
    ) -> List[Dict]:
        """Fetch articles for an arbitrary custom query string."""
        pool = fetch_pool or max(count * 3, count)
        return self._fetch_everything_query(query, pool)[:pool]

    def get_top_tech_news(
        self,
        count: int = 5,
        topic: str | Topic | None = None,
        fetch_pool: int | None = None,
    ) -> List[Dict]:
        """
        Fetch articles for a topic.

        fetch_pool: oversample so callers can drop duplicates and still fill `count`.
        """
        topic_obj = topic if isinstance(topic, Topic) else get_topic(topic)
        pool = fetch_pool or max(count * 3, count)
        articles = self._fetch_everything(topic_obj, pool)
        if topic_obj.key == DEFAULT_TOPIC and not articles:
            articles = self._fetch_headlines(pool)
        return articles[:pool]

    def _fetch_headlines(self, count: int) -> List[Dict]:
        try:
            resp = self.session.get(
                NEWSAPI_URL,
                params={
                    "category": "technology",
                    "language": "en",
                    "pageSize": min(count, 100),
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            articles = [a for a in data.get("articles", []) if self._is_valid(a)]
            logger.info("Fetched %s headline articles.", len(articles))
            return articles[:count]
        except Exception as e:
            logger.error("Headlines fetch failed: %s", e)
            return []

    def _fetch_everything_query(self, query: str, count: int) -> List[Dict]:
        try:
            resp = self.session.get(
                EVERYTHING_URL,
                params={
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": min(count, 100),
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            articles = [a for a in data.get("articles", []) if self._is_valid(a)]
            logger.info("Fetched %s articles for custom query=%s.", len(articles), query)
            return articles[:count]
        except Exception as e:
            logger.error("Custom everything fetch failed (%s): %s", query, e)
            return []

    def _fetch_everything(self, topic: Topic, count: int) -> List[Dict]:
        try:
            resp = self.session.get(
                EVERYTHING_URL,
                params={
                    "q": topic.query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": min(count, 100),
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            articles = [a for a in data.get("articles", []) if self._is_valid(a)]
            logger.info("Fetched %s articles for topic=%s.", len(articles), topic.key)
            return articles[:count]
        except Exception as e:
            logger.error("Everything fetch failed (%s): %s", topic.key, e)
            return []

    @staticmethod
    def _is_valid(article: dict) -> bool:
        title = article.get("title", "")
        return bool(title) and title != "[Removed]" and bool(article.get("url"))
