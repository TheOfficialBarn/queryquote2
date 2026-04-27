"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:

"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lowercase and remove punctuation/diacritics for punctuation-agnostic matching."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def tokenize(text: str, *, remove_stopwords: bool = True) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    tokens = normalized.split(" ")
    if not remove_stopwords:
        return tokens
    return [tok for tok in tokens if tok and tok not in STOPWORDS]


def join_tokens(tokens: Iterable[str]) -> str:
    return " ".join(tokens)
