"""Prologue:
Quote text similarity helpers shared by SQLite v1 and v2 reranking.
Last updated: 2026-04-27 - Removed deprecated in-memory phrase/proximity
helpers after dropping the pickle backend.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from .preprocessing import normalize_text


def fuzzy_ratio(query_text: str, doc_text: str) -> float:
    q = normalize_text(query_text)
    d = normalize_text(doc_text)
    if not q or not d:
        return 0.0
    return SequenceMatcher(None, q, d).ratio()
