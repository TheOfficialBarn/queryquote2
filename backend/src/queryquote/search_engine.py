from __future__ import annotations

from dataclasses import dataclass

from .config import ScoreWeights
from .indexing import IndexBundle, load_index
from .preprocessing import tokenize
from .quote_matching import fuzzy_ratio, has_exact_phrase, proximity_score
from .ranking import bm25_scores, minmax_normalize, tfidf_cosine_scores
from .types import SearchResult


@dataclass
class SearchEngine:
    bundle: IndexBundle
    weights: ScoreWeights = ScoreWeights()

    @classmethod
    def from_index_dir(cls, index_dir: str) -> "SearchEngine":
        return cls(bundle=load_index(index_dir))

    def _candidate_docs(self, query_terms: list[str]) -> set[str]:
        candidates: set[str] = set()
        for term in query_terms:
            candidates.update(self.bundle.index.postings.get(term, {}).keys())
        return candidates

    def search(self, query: str, *, top_k: int = 10) -> list[SearchResult]:
        query_terms = tokenize(query, remove_stopwords=True)
        if not query_terms:
            return []

        candidates = self._candidate_docs(query_terms)
        if not candidates:
            return []

        bm25 = bm25_scores(self.bundle.index, query_terms, candidates)
        tfidf = tfidf_cosine_scores(self.bundle.index, query_terms, candidates)
        bm25_n = minmax_normalize(bm25)
        tfidf_n = minmax_normalize(tfidf)

        base_scores: dict[str, float] = {}
        for doc_id in candidates:
            base_scores[doc_id] = (
                self.weights.bm25 * bm25_n.get(doc_id, 0.0)
                + self.weights.tfidf * tfidf_n.get(doc_id, 0.0)
            )

        # Apply quote-aware reranking only to the strongest lexical candidates.
        rerank_pool = sorted(base_scores.items(), key=lambda x: x[1], reverse=True)[:200]
        final_scores = base_scores.copy()
        passages_by_id = self.bundle.passages_by_id

        for doc_id, _ in rerank_pool:
            passage = passages_by_id.get(doc_id)
            if passage is None:
                continue

            phrase = 1.0 if has_exact_phrase(self.bundle.index, doc_id, query_terms) else 0.0
            prox = proximity_score(self.bundle.index, doc_id, query_terms)
            fuzz = fuzzy_ratio(query, passage.raw_text)

            final_scores[doc_id] += (
                self.weights.phrase_boost * phrase
                + self.weights.proximity_boost * prox
                + self.weights.fuzzy_boost * fuzz
            )

        ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results: list[SearchResult] = []

        for passage_id, score in ranked:
            passage = passages_by_id.get(passage_id)
            if passage is None:
                continue
            snippet = passage.raw_text[:220] + ("..." if len(passage.raw_text) > 220 else "")
            results.append(
                SearchResult(
                    passage_id=passage_id,
                    movie_id=passage.movie_id,
                    score=score,
                    snippet=snippet,
                    source_file=passage.source_file,
                )
            )

        return results
