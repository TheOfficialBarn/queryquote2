"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Shared score normalization helpers for SQLite-backed QueryQuote search.

Last updated: 2026-04-27 - Removed deprecated in-memory BM25/TF-IDF helpers
after dropping the pickle backend.
"""

from __future__ import annotations


def minmax_normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}
