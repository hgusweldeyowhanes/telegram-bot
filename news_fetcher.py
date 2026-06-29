import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"
EVERYTHING_URL = "https://newsapi.org/v2/everything"

TECH_KEYWORDS = (
    "artificial intelligence OR machine learning OR cybersecurity "
    "OR blockchain OR cloud computing OR robotics OR semiconductor "
    "OR Apple OR Google OR Microsoft OR OpenAI OR startup"
)


class NewsFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-Api-Key": api_key})

    def get_top_tech_news(self, count: int = 5) -> List[Dict]:
        """Fetch top tech headlines. Falls back to keyword search if needed."""
        articles = self._fetch_headlines(count)
        if not articles:
            articles = self._fetch_everything(count)
        return articles

    def _fetch_headlines(self, count: int) -> List[Dict]:
        try:
            resp = self.session.get(NEWSAPI_URL, params={
                "category": "technology",
                "language": "en",
                "pageSize": count,
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            articles = [a for a in data.get("articles", []) if self._is_valid(a)]
            logger.info(f"Fetched {len(articles)} headline articles.")
            return articles[:count]
        except Exception as e:
            logger.error(f"Headlines fetch failed: {e}")
            return []

    def _fetch_everything(self, count: int) -> List[Dict]:
        try:
            resp = self.session.get(EVERYTHING_URL, params={
                "q": TECH_KEYWORDS,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": count,
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            articles = [a for a in data.get("articles", []) if self._is_valid(a)]
            logger.info(f"Fetched {len(articles)} keyword articles.")
            return articles[:count]
        except Exception as e:
            logger.error(f"Everything fetch failed: {e}")
            return []

    @staticmethod
    def _is_valid(article: dict) -> bool:
        """Filter out removed articles and those without titles."""
        title = article.get("title", "")
        return (
            bool(title)
            and title != "[Removed]"
            and bool(article.get("url"))
        )
