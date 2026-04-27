"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Quote text similarity helpers shared by SQLite v1 and v2 reranking.

Last updated: 2026-04-27 - Added import comments explaining sequence
similarity and shared text normalization dependencies.
"""

from __future__ import annotations      # Keeps helper annotations from doing runtime work.
from difflib import SequenceMatcher     # Scores ordered quote wording similarity.
                                        # SequenceMatcher is a class that compares two sequences
                                        # and then estimates how similar they are. Most commonly,
                                        # those sequences are strings
                                        # It *REWARDS* near-identical wording, but is not vector-based/cosine-based
                                        # We chose this over cosine-similarity as quotes need semantic similarity
                                        # AND **ORDER** siimilarity, which this excels at.
from .analyzer_v1 import normalize_text # Normalizes query/document strings before fuzzy comparison.


def fuzzy_ratio(query_text: str, doc_text: str) -> float:
    # Purpose: provide a shared FUZZY QUOTE SIMILARITY helper
    # For both v1 and v2 search engines
    q = normalize_text(query_text)
    d = normalize_text(doc_text)
    if not q or not d:
        return 0.0
    return SequenceMatcher(None, q, d).ratio()
