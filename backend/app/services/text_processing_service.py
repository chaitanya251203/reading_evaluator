import re


# Keep all Unicode word characters (Latin, Devanagari, digits, etc.) + whitespace.
# Strips punctuation in any script.
_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    lowered = text.lower().replace("\n", " ")
    cleaned = _PUNCT_RE.sub(" ", lowered)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return normalized.split(" ")
