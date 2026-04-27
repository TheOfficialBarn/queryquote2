"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Version 2 text analyzer for quote-focused indexing.

Last updated: 2026-04-27 - Added review comments explaining v2 normalization,
contraction handling, and the split between full tokens and BM25 tokens.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


# Common words removed only from the BM25 ranking stream.
# Full-token phrase matching keeps these words because quotes often depend on them.
BM25_STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "am",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "can",
    "could",
    "did",
    "do",
    "does",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "our",
    "ours",
    "she",
    "so",
    "that",
    "there",
    "these",
    "the",
    "their",
    "theirs",
    "them",
    "they",
    "this",
    "those",
    "to",
    "us",
    "was",
    "we",
    "what",
    "when",
    "where",
    "who",
    "whom",
    "why",
    "were",
    "will",
    "would",
    "with",
    "you",
    "your",
    "yours",
}

# Normalize curly apostrophes/backticks before expanding contractions.
_APOSTROPHES_RE = re.compile(r"[\u2018\u2019\u201b\u2032`]")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_WHITESPACE_RE = re.compile(r"\s+")

# Irregular contractions and informal quote wording that suffix rules do not handle well.
_SPECIAL_CONTRACTIONS = {
    "ain't": "am not",
    "can't": "can not",
    "cannot": "can not",
    "gimme": "give me",
    "gonna": "going to",
    "gotta": "got to",
    "lemme": "let me",
    "let's": "let us",
    "ma'am": "madam",
    "wanna": "want to",
    "won't": "will not",
    "y'all": "you all",
}

# Generic contraction endings. These run after special cases so words like "won't"
# and "can't" get the intended expansion first.
_CONTRACTION_SUFFIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b([a-z]+)n't\b"), r"\1 not"),
    (re.compile(r"\b([a-z]+)'re\b"), r"\1 are"),
    (re.compile(r"\b([a-z]+)'ve\b"), r"\1 have"),
    (re.compile(r"\b([a-z]+)'ll\b"), r"\1 will"),
    (re.compile(r"\b([a-z]+)'d\b"), r"\1 would"),
    (re.compile(r"\b([a-z]+)'m\b"), r"\1 am"),
    (re.compile(r"\b([a-z]+)'s\b"), r"\1 is"),
)


@dataclass(frozen=True, slots=True)
class AnalyzerTokens:
    """Pair the full phrase stream with the filtered BM25 ranking stream."""

    full: list[str]
    bm25: list[str]


def normalize_for_tokens(text: str) -> str:
    """Lowercase, de-accent, expand contractions, and strip punctuation for v2."""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = _APOSTROPHES_RE.sub("'", normalized.lower())
    normalized = _expand_contractions(normalized)
    normalized = _NON_ALNUM_RE.sub(" ", normalized)
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def full_tokenize_v2(text: str) -> list[str]:
    """Return all normalized tokens for exact phrase and proximity matching."""
    normalized = normalize_for_tokens(text)
    return normalized.split(" ") if normalized else []


def bm25_tokenize_v2(text: str) -> list[str]:
    """Return only selective terms for BM25 candidate scoring."""
    return bm25_terms_from_full_tokens(full_tokenize_v2(text))


def analyze_v2(text: str) -> AnalyzerTokens:
    """Build both v2 token streams from one normalization pass."""
    full_tokens = full_tokenize_v2(text)
    return AnalyzerTokens(
        full=full_tokens,
        bm25=bm25_terms_from_full_tokens(full_tokens),
    )


def is_bm25_term(token: str) -> bool:
    """Decide whether a token is useful enough for BM25 postings."""
    return bool(token) and token not in BM25_STOPWORDS


def bm25_terms_from_full_tokens(tokens: list[str]) -> list[str]:
    """Filter full tokens down to the BM25 ranking stream."""
    return [token for token in tokens if is_bm25_term(token)]


def _expand_contractions(text: str) -> str:
    """Expand special and suffix contractions before punctuation is removed."""
    for contraction, expansion in _SPECIAL_CONTRACTIONS.items():
        text = re.sub(rf"\b{re.escape(contraction)}\b", expansion, text)

    for pattern, replacement in _CONTRACTION_SUFFIXES:
        text = pattern.sub(replacement, text)

    return text
