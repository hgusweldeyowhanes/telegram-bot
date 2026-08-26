"""Persist posted article URLs so the channel does not repeat the same story."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class DedupeStore:
    """JSON-backed URL / title fingerprint store."""

    def __init__(self, path: str | Path, max_entries: int = 500):
        self.path = Path(path)
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._seen: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            self._seen = {}
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._seen = {str(k): str(v) for k, v in data.items()}
            else:
                self._seen = {}
        except Exception as e:
            logger.warning("Could not load dedupe store %s: %s", self.path, e)
            self._seen = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Keep newest entries if we grow past the cap
        if len(self._seen) > self.max_entries:
            items = sorted(self._seen.items(), key=lambda kv: kv[1], reverse=True)
            self._seen = dict(items[: self.max_entries])
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._seen, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def fingerprint(url: str = "", title: str = "") -> str:
        raw = (url or "").strip().lower() or (title or "").strip().lower()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def is_seen(self, url: str = "", title: str = "") -> bool:
        key = self.fingerprint(url, title)
        with self._lock:
            return key in self._seen

    def mark(self, url: str = "", title: str = "") -> None:
        key = self.fingerprint(url, title)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock:
            self._seen[key] = now
            self._save()

    def filter_new(self, articles: list[dict]) -> list[dict]:
        fresh = []
        for article in articles:
            url = article.get("url") or ""
            title = article.get("title") or ""
            if self.is_seen(url, title):
                continue
            fresh.append(article)
        return fresh

    def mark_many(self, articles: list[dict]) -> None:
        for article in articles:
            self.mark(article.get("url") or "", article.get("title") or "")

    def count(self) -> int:
        with self._lock:
            return len(self._seen)
