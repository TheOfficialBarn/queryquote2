from __future__ import annotations

from difflib import SequenceMatcher

from .indexing import InvertedPositionalIndex
from .preprocessing import normalize_text


def has_exact_phrase(index: InvertedPositionalIndex, doc_id: str, query_terms: list[str]) -> bool:
    if not query_terms:
        return False
    if any(doc_id not in index.postings.get(t, {}) for t in query_terms):
        return False

    first_positions = index.postings[query_terms[0]][doc_id]
    offsets = range(1, len(query_terms))
    for p in first_positions:
        if all((p + off) in index.postings[query_terms[off]][doc_id] for off in offsets):
            return True
    return False


def proximity_score(
    index: InvertedPositionalIndex,
    doc_id: str,
    query_terms: list[str],
    *,
    window: int = 8,
) -> float:
    if len(query_terms) < 2:
        return 0.0

    positions_by_term = []
    for term in query_terms:
        pos = index.postings.get(term, {}).get(doc_id)
        if not pos:
            return 0.0
        positions_by_term.append(pos)

    flattened = []
    for i, pos_list in enumerate(positions_by_term):
        for p in pos_list:
            flattened.append((p, i))
    flattened.sort(key=lambda x: x[0])

    required = len(query_terms)
    counts = [0] * required
    covered = 0
    best_span = None
    left = 0

    for right, (pos_r, idx_r) in enumerate(flattened):
        counts[idx_r] += 1
        if counts[idx_r] == 1:
            covered += 1

        while covered == required and left <= right:
            pos_l, idx_l = flattened[left]
            span = pos_r - pos_l + 1
            if best_span is None or span < best_span:
                best_span = span

            counts[idx_l] -= 1
            if counts[idx_l] == 0:
                covered -= 1
            left += 1

    if best_span is None:
        return 0.0
    if best_span <= window:
        return 1.0
    return window / best_span


def fuzzy_ratio(query_text: str, doc_text: str) -> float:
    q = normalize_text(query_text)
    d = normalize_text(doc_text)
    if not q or not d:
        return 0.0
    return SequenceMatcher(None, q, d).ratio()
