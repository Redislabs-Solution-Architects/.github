from __future__ import annotations

import re
from typing import Iterable, Optional

QUESTION_STARTERS = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    "can",
    "could",
    "would",
    "should",
    "do",
    "does",
    "did",
    "is",
    "are",
    "will",
    "have",
    "has",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def is_question(text: str, min_len: int = 12) -> bool:
    cleaned = _normalize(text)
    if len(cleaned) < min_len:
        return False
    lowered = cleaned.lower()
    if lowered.endswith("?"):
        return True
    if any(lowered.startswith(f"{starter} ") for starter in QUESTION_STARTERS):
        return True
    return "can you" in lowered or "could you" in lowered


def newest_question(texts: Iterable[str], min_len: int = 12) -> Optional[str]:
    for text in reversed(list(texts)):
        if is_question(text, min_len=min_len):
            return _normalize(text)
    return None

