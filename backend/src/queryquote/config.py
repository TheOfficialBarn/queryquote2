from __future__ import annotations

from dataclasses import dataclass


DEFAULT_MAX_PASSAGE_TOKENS = 120
DEFAULT_PASSAGE_OVERLAP = 20
DEFAULT_TOP_K = 10


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    bm25: float = 0.65
    tfidf: float = 0.35
    phrase_boost: float = 0.25
    proximity_boost: float = 0.20
    fuzzy_boost: float = 0.20
