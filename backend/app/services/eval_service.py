from __future__ import annotations

import math

from jiwer import Compose, RemoveMultipleSpaces, RemovePunctuation, Strip, ToLowerCase, process_words

from app.services.alignment_service import align_words
from app.services.text_processing_service import tokenize

_TRANSFORM = Compose(
    [
        ToLowerCase(),
        RemovePunctuation(),
        RemoveMultipleSpaces(),
        Strip(),
    ]
)


def _normalize_text(text: str) -> str:
    return _TRANSFORM(text or "")


def _word_stats(reference_text: str, hypothesis_text: str) -> dict:
    ref = _normalize_text(reference_text)
    hyp = _normalize_text(hypothesis_text)
    measures = process_words(ref, hyp)

    total_words = measures.hits + measures.substitutions + measures.deletions
    spoken_words = measures.hits + measures.substitutions + measures.insertions

    if total_words == 0:
        accuracy = 0.0
        completion = 0.0
    else:
        accuracy = (measures.hits / total_words) * 100
        completion = min((spoken_words / total_words) * 100, 100.0)

    return {
        "total_words": total_words,
        "spoken_words": spoken_words,
        "accuracy": round(accuracy, 1),
        "completion": round(completion, 1),
    }


def _fluency_score(segments: list[dict]) -> float:
    if not segments:
        return 70.0

    pauses = []
    for index in range(1, len(segments)):
        gap = segments[index]["start"] - segments[index - 1]["end"]
        if gap > 0:
            pauses.append(gap)

    long_pauses = sum(1 for gap in pauses if gap >= 1.2)
    medium_pauses = sum(1 for gap in pauses if 0.6 <= gap < 1.2)

    score = 100 - long_pauses * 12 - medium_pauses * 6
    return round(max(40.0, min(100.0, score)), 1)


def _pace_score(spoken_words: int, duration_seconds: float) -> tuple[float, float]:
    if duration_seconds <= 0 or spoken_words <= 0:
        return 0.0, 70.0

    wpm = spoken_words / (duration_seconds / 60)

    if 60 <= wpm <= 130:
        score = 100.0
    elif wpm < 60:
        if wpm <= 40:
            score = 60.0
        else:
            score = 60.0 + (wpm - 40) * 2
    else:
        score = max(60.0, 100.0 - (wpm - 130) * 1.5)

    return round(wpm, 1), round(min(100.0, max(60.0, score)), 1)


def _pronunciation_score(segments: list[dict]) -> float:
    logprobs = [seg.get("avg_logprob") for seg in segments if seg.get("avg_logprob") is not None]
    if not logprobs:
        return 70.0

    avg_logprob = sum(logprobs) / len(logprobs)
    confidence = math.exp(avg_logprob)
    score = min(100.0, max(60.0, confidence * 120))
    return round(score, 1)


def _grade_for_score(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "E"


def evaluate_reading(
    passage_text: str,
    transcript: str,
    segments: list[dict],
    duration_seconds: float,
) -> dict:
    exp_words = tokenize(passage_text)
    spk_words = tokenize(transcript)

    # Use our alignment service (Hindi-aware) for accuracy
    if exp_words and spk_words:
        alignment = align_words(exp_words, spk_words)
        correct = alignment["correct_count"]
        wrong = alignment["wrong_count"]
        total = len(exp_words)
        accuracy = round((correct / total) * 100, 1) if total > 0 else 0.0
        completion = round(min(((correct + wrong) / total) * 100, 100.0), 1) if total > 0 else 0.0
        wrong_words = [
            exp_words[i]
            for i, s in enumerate(alignment["statuses"])
            if s == "wrong"
        ]
    else:
        accuracy = 0.0
        completion = 0.0
        wrong_words = []

    fluency = _fluency_score(segments)
    pace_wpm, pace_score = _pace_score(len(spk_words), duration_seconds)
    pronunciation = _pronunciation_score(segments)

    final_score = (
        0.45 * accuracy
        + 0.25 * fluency
        + 0.15 * completion
        + 0.10 * pace_score
        + 0.05 * pronunciation
    )

    final_score = round(final_score, 1)
    grade = _grade_for_score(final_score)

    return {
        "accuracy": accuracy,
        "fluency": fluency,
        "completion": completion,
        "pace_wpm": pace_wpm,
        "pace_score": pace_score,
        "pronunciation": pronunciation,
        "final_score": final_score,
        "grade": grade,
        "wrong_words": wrong_words,
    }
