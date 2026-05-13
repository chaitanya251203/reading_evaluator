"""
AI service using OpenAI API (gpt-4o-mini).
Set OPENAI_API_KEY in your .env file.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("reading_assessment")

_client = None
_client_key = None  # track which key the client was created with


def _get_client():
    global _client, _client_key
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("ai_service: OPENAI_API_KEY not set — AI features disabled")
        return None
    # Re-create client if key changed (e.g. after hot-reload)
    if _client is not None and _client_key == api_key:
        return _client
    try:
        from openai import OpenAI  # type: ignore
        _client = OpenAI(api_key=api_key, timeout=30.0)
        _client_key = api_key
        logger.info("ai_service: OpenAI client initialized (key=%s...)", api_key[:12])
        return _client
    except Exception as exc:
        logger.error("ai_service: failed to init OpenAI client: %s", exc, exc_info=True)
        return None


_MODEL = "gpt-4o-mini"


def _chat(prompt: str, max_tokens: int = 300) -> str:
    client = _get_client()
    if not client:
        logger.error("ai_service: no client available")
        return ""
    try:
        logger.info("ai_service: calling %s (max_tokens=%s)", _MODEL, max_tokens)
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        result = resp.choices[0].message.content.strip()
        logger.info("ai_service: success, response length=%d", len(result))
        return result
    except Exception as exc:
        logger.error("ai_service: API call failed: %s", exc, exc_info=True)
        return ""


def generate_session_overview(
    passage_text: str,
    transcript: str,
    metrics: dict,
    wrong_words: list[str],
) -> str:
    """Return a 2–3 sentence improvement overview for a reading session."""
    ww = ", ".join(wrong_words[:10]) if wrong_words else "none"
    prompt = (
        f"You are a friendly reading coach for young children. "
        f"A child just read a passage aloud. Here are their results:\n"
        f"- Accuracy: {metrics.get('accuracy', 0)}%\n"
        f"- Fluency: {metrics.get('fluency', 0)}%\n"
        f"- Pace: {metrics.get('pace_wpm', 0)} wpm\n"
        f"- Grade: {metrics.get('grade', 'E')}\n"
        f"- Words read incorrectly: {ww}\n\n"
        f"Write 2–3 encouraging, specific sentences telling the child what they did well "
        f"and what they should focus on improving. Keep it simple and positive."
    )
    return _chat(prompt, max_tokens=150)


def generate_practice_story(wrong_words: list[str], language: str = "english") -> str:
    """Generate a short 1-paragraph practice story using the given wrong words."""
    if not wrong_words:
        return ""
    ww = ", ".join(wrong_words[:15])
    is_hindi = "hindi" in language.lower()

    if is_hindi:
        lang_instruction = (
            "Write ONLY in Hindi (Devanagari script). "
            "Do NOT use any English words at all. "
            "The entire story must be written purely in Hindi."
        )
    else:
        lang_instruction = (
            "Write ONLY in English. "
            "Do NOT use any Hindi or Devanagari words at all. "
            "The entire story must be written purely in English."
        )

    prompt = (
        f"You are a children's story writer. Write a single short paragraph story "
        f"suitable for a primary school child. "
        f"LANGUAGE RULE (STRICT): {lang_instruction} "
        f"The story MUST naturally include as many of these focus words as possible: {ww}. "
        f"Keep it fun, simple, 60-80 words. Output only the story paragraph, nothing else."
    )
    return _chat(prompt, max_tokens=250)
