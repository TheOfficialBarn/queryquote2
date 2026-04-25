from __future__ import annotations

import math
import pickle
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .preprocessing import tokenize
from .types import Passage


@dataclass
class InvertedPositionalIndex:
    postings: dict[str, dict[str, list[int]]] = field(default_factory=lambda: defaultdict(dict))
    doc_lengths: dict[str, int] = field(default_factory=dict)
    doc_term_freqs: dict[str, dict[str, int]] = field(default_factory=dict)
    doc_freqs: dict[str, int] = field(default_factory=dict)
    doc_norms: dict[str, float] = field(default_factory=dict)
    avg_doc_len: float = 0.0
    num_docs: int = 0

    def add_document(self, doc_id: str, tokens: list[str]) -> None:
        term_positions: dict[str, list[int]] = defaultdict(list)
        for pos, term in enumerate(tokens):
            term_positions[term].append(pos)

        self.doc_lengths[doc_id] = len(tokens)
        term_freqs = {term: len(pos_list) for term, pos_list in term_positions.items()}
        self.doc_term_freqs[doc_id] = term_freqs

        for term, pos_list in term_positions.items():
            self.postings[term][doc_id] = pos_list

    def finalize(self) -> None:
        self.num_docs = len(self.doc_lengths)
        self.avg_doc_len = (
            sum(self.doc_lengths.values()) / self.num_docs if self.num_docs else 0.0
        )

        self.doc_freqs = {
            term: len(doc_dict) for term, doc_dict in self.postings.items()
        }

        self.doc_norms = {}
        for doc_id, term_freqs in self.doc_term_freqs.items():
            sq_sum = 0.0
            for term, tf in term_freqs.items():
                df = self.doc_freqs.get(term, 0)
                if not df:
                    continue
                idf = math.log((self.num_docs + 1) / (df + 1)) + 1.0
                weight = (1.0 + math.log(tf)) * idf
                sq_sum += weight * weight
            self.doc_norms[doc_id] = math.sqrt(sq_sum) if sq_sum > 0 else 1e-9


@dataclass
class IndexBundle:
    index: InvertedPositionalIndex
    passages: list[Passage]

    @property
    def passages_by_id(self) -> dict[str, Passage]:
        return {p.passage_id: p for p in self.passages}


def build_index(passages: list[Passage]) -> InvertedPositionalIndex:
    idx = InvertedPositionalIndex()
    for passage in passages:
        tokens = tokenize(passage.raw_text, remove_stopwords=True)
        idx.add_document(passage.passage_id, tokens)
    idx.finalize()
    return idx


def save_index(bundle: IndexBundle, output_dir: str | Path) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    file_path = out / "index_bundle.pkl"
    with file_path.open("wb") as f:
        pickle.dump(bundle, f)


def load_index(index_dir: str | Path) -> IndexBundle:
    file_path = Path(index_dir) / "index_bundle.pkl"
    with file_path.open("rb") as f:
        bundle: IndexBundle = pickle.load(f)
    return bundle
