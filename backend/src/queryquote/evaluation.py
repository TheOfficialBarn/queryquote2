"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:

"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path


def load_queries(path: str | Path) -> list[dict[str, str]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_qrels(path: str | Path) -> dict[str, dict[str, int]]:
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            qrels[row["qid"]][row["doc_id"]] = int(row.get("relevance", 1))
    return dict(qrels)


def precision_at_k(ranked_ids: list[str], rel: dict[str, int], k: int) -> float:
    if k <= 0:
        return 0.0
    hit = sum(1 for doc_id in ranked_ids[:k] if rel.get(doc_id, 0) > 0)
    return hit / k


def recall_at_k(ranked_ids: list[str], rel: dict[str, int], k: int) -> float:
    total_rel = sum(1 for v in rel.values() if v > 0)
    if total_rel == 0:
        return 0.0
    hit = sum(1 for doc_id in ranked_ids[:k] if rel.get(doc_id, 0) > 0)
    return hit / total_rel


def average_precision(ranked_ids: list[str], rel: dict[str, int]) -> float:
    num_rel = 0
    acc = 0.0
    for i, doc_id in enumerate(ranked_ids, start=1):
        if rel.get(doc_id, 0) > 0:
            num_rel += 1
            acc += num_rel / i
    total_rel = sum(1 for v in rel.values() if v > 0)
    if total_rel == 0:
        return 0.0
    return acc / total_rel


def reciprocal_rank(ranked_ids: list[str], rel: dict[str, int]) -> float:
    for i, doc_id in enumerate(ranked_ids, start=1):
        if rel.get(doc_id, 0) > 0:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_ids: list[str], rel: dict[str, int], k: int) -> float:
    def dcg(items: list[int]) -> float:
        return sum((gain / math.log2(i + 2)) for i, gain in enumerate(items))

    gains = [rel.get(doc_id, 0) for doc_id in ranked_ids[:k]]
    ideal = sorted(rel.values(), reverse=True)[:k]
    ideal_dcg = dcg(ideal)
    if ideal_dcg == 0:
        return 0.0
    return dcg(gains) / ideal_dcg


def evaluate_run(
    run: dict[str, list[str]],
    qrels: dict[str, dict[str, int]],
    *,
    k: int,
) -> dict[str, float]:
    ap_scores = []
    rr_scores = []
    ndcg_scores = []
    p_scores = []
    r_scores = []

    for qid, rel in qrels.items():
        ranked = run.get(qid, [])
        ap_scores.append(average_precision(ranked, rel))
        rr_scores.append(reciprocal_rank(ranked, rel))
        ndcg_scores.append(ndcg_at_k(ranked, rel, k))
        p_scores.append(precision_at_k(ranked, rel, k))
        r_scores.append(recall_at_k(ranked, rel, k))

    n = max(len(qrels), 1)
    return {
        "MAP": sum(ap_scores) / n,
        "MRR": sum(rr_scores) / n,
        f"nDCG@{k}": sum(ndcg_scores) / n,
        f"P@{k}": sum(p_scores) / n,
        f"R@{k}": sum(r_scores) / n,
    }
