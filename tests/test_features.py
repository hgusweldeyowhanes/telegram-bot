import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dedupe import DedupeStore
from formatter import format_digest_body, format_digest_header
from summarizer import Summarizer, clean_description
from topics import TOPICS, get_topic, list_topics_help


class TopicsTests(unittest.TestCase):
    def test_known_topics(self):
        self.assertIn("ai", TOPICS)
        self.assertIn("cyber", TOPICS)
        self.assertEqual(get_topic("AI").key, "ai")

    def test_unknown_falls_back_to_tech(self):
        self.assertEqual(get_topic("nope").key, "tech")

    def test_help_lists_commands(self):
        help_text = list_topics_help()
        self.assertIn("/ai", help_text)
        self.assertIn("/cyber", help_text)


class DedupeTests(unittest.TestCase):
    def test_marks_and_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seen.json"
            store = DedupeStore(path)
            articles = [
                {"title": "A", "url": "https://example.com/a"},
                {"title": "B", "url": "https://example.com/b"},
            ]
            store.mark_many(articles[:1])
            fresh = store.filter_new(articles)
            self.assertEqual(len(fresh), 1)
            self.assertEqual(fresh[0]["url"], "https://example.com/b")
            self.assertTrue(path.is_file())

    def test_title_fallback_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DedupeStore(Path(tmp) / "seen.json")
            store.mark(url="", title="Same Title")
            self.assertTrue(store.is_seen(url="", title="same title"))


class SummarizerTests(unittest.TestCase):
    def test_clean_description_truncates(self):
        text = "x" * 400
        out = clean_description(text, limit=50)
        self.assertTrue(out.endswith("..."))
        self.assertLessEqual(len(out), 50)

    def test_disabled_without_key(self):
        s = Summarizer(api_key="", enabled=True)
        self.assertFalse(s.available)
        article = {"title": "T", "description": "Hello world from the wire."}
        self.assertIn("Hello", s.summarize_article(article))

    @patch("summarizer.requests.post")
    def test_openai_path(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "AI firms race to ship smaller models."}}]
        }
        mock_post.return_value = mock_resp
        s = Summarizer(api_key="sk-test", enabled=True)
        out = s.summarize_article({"title": "News", "description": "Long text"})
        self.assertIn("AI firms", out)
        mock_post.assert_called_once()


class FormatterTests(unittest.TestCase):
    def test_digest_contains_titles(self):
        topic = get_topic("ai")
        articles = [
            {
                "title": "OpenAI ships update",
                "summary": "A short blurb.",
                "url": "https://example.com/1",
                "source": {"name": "Example"},
            }
        ]
        body = format_digest_body(articles, topic)
        self.assertIn("OpenAI ships update", body)
        self.assertIn("AI & ML", format_digest_header(topic, 1))
        self.assertIn("1 story", format_digest_header(topic, 1))
        self.assertIn("2 stories", format_digest_header(topic, 2))


class NewsFetcherTopicTests(unittest.TestCase):
    def test_everything_uses_topic_query(self):
        from news_fetcher import NewsFetcher

        fetcher = NewsFetcher("fake-key")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "articles": [
                {
                    "title": "Breach at firm",
                    "url": "https://example.com/c",
                    "description": "Details",
                    "source": {"name": "SecNews"},
                    "publishedAt": "2026-08-26T10:00:00Z",
                }
            ]
        }
        with patch.object(fetcher.session, "get", return_value=mock_resp) as mock_get:
            articles = fetcher.get_top_tech_news(count=1, topic="cyber")
            self.assertEqual(len(articles), 1)
            kwargs = mock_get.call_args.kwargs
            self.assertIn("cybersecurity", kwargs["params"]["q"])


if __name__ == "__main__":
    unittest.main()
