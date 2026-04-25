from __future__ import annotations

import math
from collections import Counter, defaultdict

from .indexing import InvertedPositionalIndex


def tfidf_cosine_scores(
    index: InvertedPositionalIndex,
    query_terms: list[str],
    candidate_docs: set[str] | None = None,
) -> dict[str, float]:
    if not query_terms:
        return {}

    q_tf = Counter(query_terms)
    q_weights: dict[str, float] = {}
    for term, tf in q_tf.items():
        df = index.doc_freqs.get(term, 0)
        if not df:
            continue
        idf = math.log((index.num_docs + 1) / (df + 1)) + 1.0
        q_weights[term] = (1.0 + math.log(tf)) * idf

    q_norm = math.sqrt(sum(w * w for w in q_weights.values())) or 1e-9
    scores: dict[str, float] = defaultdict(float)

    for term, q_w in q_weights.items():
        postings = index.postings.get(term, {})
        df = index.doc_freqs.get(term, 0)
        idf = math.log((index.num_docs + 1) / (df + 1)) + 1.0
        for doc_id, positions in postings.items():
            if candidate_docs is not None and doc_id not in candidate_docs:
                continue
            d_tf = len(positions)
            d_w = (1.0 + math.log(d_tf)) * idf
            scores[doc_id] += q_w * d_w

    for doc_id in list(scores.keys()):
        scores[doc_id] = scores[doc_id] / (q_norm * index.doc_norms.get(doc_id, 1e-9))

    return dict(scores)


def bm25_scores(
    index: InvertedPositionalIndex,
    query_terms: list[str],
    candidate_docs: set[str] | None = None,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> dict[str, float]:
    if not query_terms:
        return {}

    q_tf = Counter(query_terms)
    scores: dict[str, float] = defaultdict(float)

    for term, q_weight in q_tf.items():
        df = index.doc_freqs.get(term, 0)
        if not df:
            continue
        idf = math.log(1.0 + ((index.num_docs - df + 0.5) / (df + 0.5)))
        postings = index.postings.get(term, {})
        for doc_id, positions in postings.items():
            if candidate_docs is not None and doc_id not in candidate_docs:
                continue

            tf = len(positions)
            dl = index.doc_lengths.get(doc_id, 0)
            denom = tf + k1 * (1 - b + b * (dl / (index.avg_doc_len or 1.0)))
            term_score = idf * ((tf * (k1 + 1)) / (denom or 1e-9))
            scores[doc_id] += term_score * q_weight

    return dict(scores)


def minmax_normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}
