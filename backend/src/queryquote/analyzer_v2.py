"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Version 2 text analyzer for quote-focused indexing.

Last updated: 2026-04-26 - Adds contraction expansion and separate full-token
and BM25-token streams so phrase matching can keep stopwords while ranking can
stay selective.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


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

_APOSTROPHES_RE = re.compile(r"[\u2018\u2019\u201b\u2032`]")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_WHITESPACE_RE = re.compile(r"\s+")
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
    full: list[str]
    bm25: list[str]


def normalize_for_tokens(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = _APOSTROPHES_RE.sub("'", normalized.lower())
    normalized = _expand_contractions(normalized)
    normalized = _NON_ALNUM_RE.sub(" ", normalized)
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def full_tokenize_v2(text: str) -> list[str]:
    normalized = normalize_for_tokens(text)
    return normalized.split(" ") if normalized else []


def bm25_tokenize_v2(text: str) -> list[str]:
    return bm25_terms_from_full_tokens(full_tokenize_v2(text))


def analyze_v2(text: str) -> AnalyzerTokens:
    full_tokens = full_tokenize_v2(text)
    return AnalyzerTokens(
        full=full_tokens,
        bm25=bm25_terms_from_full_tokens(full_tokens),
    )


def is_bm25_term(token: str) -> bool:
    return bool(token) and token not in BM25_STOPWORDS


def bm25_terms_from_full_tokens(tokens: list[str]) -> list[str]:
    return [token for token in tokens if is_bm25_term(token)]


def _expand_contractions(text: str) -> str:
    for contraction, expansion in _SPECIAL_CONTRACTIONS.items():
        text = re.sub(rf"\b{re.escape(contraction)}\b", expansion, text)

    for pattern, replacement in _CONTRACTION_SUFFIXES:
        text = pattern.sub(replacement, text)

    return text
