from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Passage:
    passage_id: str
    movie_id: str
    source_file: str
    raw_text: str


@dataclass(slots=True)
class SearchResult:
    passage_id: str
    movie_id: str
    score: float
    snippet: str
    source_file: str


@dataclass(slots=True)
class Qrel:
    qid: str
    doc_id: str
    relevance: int
