import re
import unicodedata

from rapidfuzz import fuzz

from app.services.text_processing_service import normalize_text


MATCH_THRESHOLD = 50


def _clean_word(word: str) -> str:
    """Aggressive normalization for Hindi+English: strip diacritics, punctuation, matras."""
    if not word:
        return ""
    w = word.lower().strip()
    # Remove Devanagari dandas, visarga, anusvara, nukta, halant, chandrabindu
    w = re.sub(r'[\u0901\u0902\u0903\u093C\u094D\u0964\u0965]', '', w)
    # Remove all non-letter/non-digit characters
    w = re.sub(r'[^\w]', '', w, flags=re.UNICODE)
    # Normalize unicode (NFC)
    w = unicodedata.normalize('NFC', w)
    return w.strip()


def _is_match(expected: str, spoken: str) -> bool:
    if not expected or not spoken:
        return False
    e = _clean_word(expected)
    s = _clean_word(spoken)
    if not e or not s:
        return False
    # Exact match after cleaning
    if e == s:
        return True
    # One starts with the other (prefix match for partial words)
    if len(e) > 2 and len(s) > 2 and (e.startswith(s) or s.startswith(e)):
        return True
    # Fuzzy ratio
    return fuzz.ratio(e, s) >= MATCH_THRESHOLD


def align_words(expected_words: list[str], spoken_words: list[str]) -> dict:
    statuses = ["unread"] * len(expected_words)
    ei = 0
    si = 0
    LOOK = 4  # look-ahead window

    while ei < len(expected_words) and si < len(spoken_words):
        if _is_match(expected_words[ei], spoken_words[si]):
            statuses[ei] = "correct"
            ei += 1
            si += 1
            continue

        # Try skipping expected words (student skipped them)
        found = False
        for k in range(1, LOOK + 1):
            if ei + k < len(expected_words) and _is_match(expected_words[ei + k], spoken_words[si]):
                for j in range(ei, ei + k):
                    statuses[j] = "wrong"
                ei += k
                found = True
                break
        if found:
            continue

        # Try skipping spoken words (student said extra words)
        for k in range(1, LOOK + 1):
            if si + k < len(spoken_words) and _is_match(expected_words[ei], spoken_words[si + k]):
                si += k
                found = True
                break
        if found:
            continue

        statuses[ei] = "wrong"
        ei += 1
        si += 1

    current_index = ei if ei < len(expected_words) else len(expected_words) - 1
    correct_count = sum(1 for s in statuses if s == "correct")
    wrong_count = sum(1 for s in statuses if s == "wrong")

    return {
        "statuses": statuses,
        "current_index": max(0, current_index),
        "correct_count": correct_count,
        "wrong_count": wrong_count,
    }
