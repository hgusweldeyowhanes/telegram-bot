"""Named tech topics for filtered news fetches."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    key: str
    title: str
    query: str
    emoji: str


TOPICS: dict[str, Topic] = {
    "tech": Topic(
        key="tech",
        title="Tech",
        emoji="💻",
        query=(
            "artificial intelligence OR machine learning OR cybersecurity "
            "OR blockchain OR cloud computing OR robotics OR semiconductor "
            "OR Apple OR Google OR Microsoft OR OpenAI OR startup"
        ),
    ),
    "ai": Topic(
        key="ai",
        title="AI & ML",
        emoji="🤖",
        query=(
            "artificial intelligence OR machine learning OR OpenAI OR "
            "ChatGPT OR LLM OR generative AI OR neural network"
        ),
    ),
    "cyber": Topic(
        key="cyber",
        title="Cybersecurity",
        emoji="🔐",
        query=(
            "cybersecurity OR ransomware OR data breach OR malware OR "
            "zero-day OR hacking OR infosec"
        ),
    ),
    "startups": Topic(
        key="startups",
        title="Startups",
        emoji="🚀",
        query=(
            "startup OR venture capital OR Series A OR Series B OR "
            "funding round OR unicorn OR Y Combinator"
        ),
    ),
    "cloud": Topic(
        key="cloud",
        title="Cloud & DevOps",
        emoji="☁️",
        query=(
            "cloud computing OR AWS OR Azure OR Google Cloud OR Kubernetes "
            "OR DevOps OR SaaS"
        ),
    ),
    "gadgets": Topic(
        key="gadgets",
        title="Gadgets",
        emoji="📱",
        query=(
            "iPhone OR Android OR smartphone OR laptop OR wearable OR "
            "consumer electronics OR gadget"
        ),
    ),
}

DEFAULT_TOPIC = "tech"


def get_topic(key: str | None) -> Topic:
    if not key:
        return TOPICS[DEFAULT_TOPIC]
    return TOPICS.get(key.lower().strip(), TOPICS[DEFAULT_TOPIC])


def list_topics_help() -> str:
    lines = [f"/{t.key} – {t.emoji} {t.title}" for t in TOPICS.values()]
    return "\n".join(lines)
