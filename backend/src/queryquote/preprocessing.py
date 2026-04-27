"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Purpose is to standardize text before the system indexes, searches,
splits passages, and does fuzzy matching.
As of now (4/27/26), it's used by passages.py, db_index.py, and quote_matching.py
"""
from __future__ import annotations
import re
import unicodedata
from collections.abc import Iterable


# Common words removed during search/index tokenization when
# remove_stopwords=True
# 
# These words usually don't help much in ranking since they appear everywhere
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

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")     # Finds punctuation/symbols
_WHITESPACE_RE = re.compile(r"\s+")             # Finds repeated whitespace


def normalize_text(text: str) -> str:
    """
    Lowercase and remove punctuation/diacritics for punctuation-agnostic matching.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def tokenize(text: str, *, remove_stopwords: bool = True) -> list[str]:
    """
    Turns text into normalized tokens
    """
    normalized = normalize_text(text)
    if not normalized: return []

    tokens = normalized.split(" ")              # Splits text into tokens
    if not remove_stopwords: return tokens      # Skips stopword removal
                                                # Below incorporates it
    return [tok for tok in tokens if tok and tok not in STOPWORDS]


def join_tokens(tokens: Iterable[str]) -> str:
    """
    Joins tokens back into a **STRING**
    """
    return " ".join(tokens)
