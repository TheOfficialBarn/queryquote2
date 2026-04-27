"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
SQLite-backed indexing and search for large QueryQuote transcript corpora.

Last updated: 2026-04-26 - Uses authoritative early exact-phrase detection,
rare-term recovery, and stronger quote reranking while keeping BM25 seeding fast.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import json
import math
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path

from .authority import AuthorityIndex, load_default_authority_index
from .config import DEFAULT_TOP_K
from .passages import iter_transcript_files, movie_id_from_filename, split_text_into_passages
from .preprocessing import tokenize
from .quote_matching import fuzzy_ratio
from .ranking import minmax_normalize
from .types import SearchResult


DEFAULT_TIMING_LOG_PATH = Path(__file__).resolve().parents[3] / "test" / "time-logs" / "times-v1.txt"
MAX_BM25_CANDIDATES = 10000
RERANK_POOL_SIZE = 500
MAX_SEED_TERMS = 8
MAX_SEED_TERM_DF = 250000
MAX_EXACT_PHRASE_SEED_POSTINGS = 120000
MAX_EXACT_PHRASE_TERMS = 6
FALLBACK_SEED_TERMS = 3
EXACT_PHRASE_BOOST = 1.75
EXACT_PHRASE_BASE_WEIGHT = 0.10
PROXIMITY_BOOST = 0.55
COVERAGE_BOOST = 0.20
FUZZY_BOOST = 0.15
EXACT_AUTHORITY_BOOST = 0.35


@dataclass(slots=True)
class _QueryTimingLog:
    query: str
    authority_filter: bool = False
    log_path: Path = DEFAULT_TIMING_LOG_PATH
    metrics: list[tuple[str, float]] = field(default_factory=list)

    def record(self, label: str, started_at: float) -> None:
        self.metrics.append((label, time.perf_counter() - started_at))

    def append(self, total_seconds: float) -> None:
        authority_label = "On" if self.authority_filter else "Off"
        lines = [f'Query: "{self.query}" | Authority Boost: {authority_label}']
        lines.extend(
            f"{label}: {duration:.6f}s"
            for index, (label, duration) in enumerate(self.metrics, start=1)
        )
        lines.extend(
            [
                "---",
                f"Total Time: {total_seconds:.6f}s",
                "_________________________",
            ]
        )

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write("\n".join(lines))
                handle.write("\n")
        except OSError:
            # Search should keep working even if timing diagnostics cannot be written.
            return


def _record_timing(
    timing: _QueryTimingLog | None,
    label: str,
    started_at: float,
) -> None:
    if timing is not None:
        timing.record(label, started_at)


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS passages (
            passage_id TEXT PRIMARY KEY,
            movie_id TEXT NOT NULL,
            source_file TEXT NOT NULL,
            raw_text TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS doc_stats (
            passage_id TEXT PRIMARY KEY,
            doc_len INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS postings (
            term TEXT NOT NULL,
            passage_id TEXT NOT NULL,
            tf INTEGER NOT NULL,
            positions TEXT NOT NULL,
            PRIMARY KEY (term, passage_id)
        );

        CREATE INDEX IF NOT EXISTS idx_postings_term ON postings(term);
        CREATE INDEX IF NOT EXISTS idx_postings_passage ON postings(passage_id);

        CREATE TABLE IF NOT EXISTS term_stats (
            term TEXT PRIMARY KEY,
            df INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def build_sqlite_index(
    *,
    data_dir: str | Path,
    output_dir: str | Path,
    max_passage_tokens: int,
    passage_overlap: int,
    progress_every_files: int = 500,
) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "index.db"

    if db_path.exists():
        db_path.unlink()

    conn = _connect(db_path)
    _create_schema(conn)

    term_df: Counter[str] = Counter()
    insert_passages: list[tuple[str, str, str, str]] = []
    insert_doc_stats: list[tuple[str, int]] = []
    insert_postings: list[tuple[str, str, int, str]] = []

    total_docs = 0
    total_doc_len = 0
    files_seen = 0
    start = time.time()

    for file_path in iter_transcript_files(data_dir):
        files_seen += 1
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        movie_id = movie_id_from_filename(Path(file_path).name)
        chunks = split_text_into_passages(
            text,
            max_tokens=max_passage_tokens,
            overlap=passage_overlap,
        )

        for i, chunk in enumerate(chunks):
            passage_id = f"{movie_id}::p{i:04d}"
            insert_passages.append((passage_id, movie_id, str(file_path), chunk))

            tokens = tokenize(chunk, remove_stopwords=True)
            doc_len = len(tokens)
            insert_doc_stats.append((passage_id, doc_len))
            total_docs += 1
            total_doc_len += doc_len

            term_positions: dict[str, list[int]] = defaultdict(list)
            for pos, term in enumerate(tokens):
                term_positions[term].append(pos)

            for term, pos_list in term_positions.items():
                term_df[term] += 1
                insert_postings.append(
                    (term, passage_id, len(pos_list), json.dumps(pos_list, separators=(",", ":")))
                )

        if files_seen % progress_every_files == 0:
            conn.executemany(
                "INSERT OR REPLACE INTO passages(passage_id, movie_id, source_file, raw_text) VALUES (?, ?, ?, ?)",
                insert_passages,
            )
            conn.executemany(
                "INSERT OR REPLACE INTO doc_stats(passage_id, doc_len) VALUES (?, ?)",
                insert_doc_stats,
            )
            conn.executemany(
                "INSERT OR REPLACE INTO postings(term, passage_id, tf, positions) VALUES (?, ?, ?, ?)",
                insert_postings,
            )
            conn.commit()
            insert_passages.clear()
            insert_doc_stats.clear()
            insert_postings.clear()

            elapsed = time.time() - start
            print(
                f"[build-sqlite] files={files_seen} docs={total_docs} elapsed={elapsed:.1f}s"
            )

    if insert_passages:
        conn.executemany(
            "INSERT OR REPLACE INTO passages(passage_id, movie_id, source_file, raw_text) VALUES (?, ?, ?, ?)",
            insert_passages,
        )
        conn.executemany(
            "INSERT OR REPLACE INTO doc_stats(passage_id, doc_len) VALUES (?, ?)",
            insert_doc_stats,
        )
        conn.executemany(
            "INSERT OR REPLACE INTO postings(term, passage_id, tf, positions) VALUES (?, ?, ?, ?)",
            insert_postings,
        )
        conn.commit()

    conn.executemany(
        "INSERT OR REPLACE INTO term_stats(term, df) VALUES (?, ?)",
        [(term, df) for term, df in term_df.items()],
    )

    avg_doc_len = (total_doc_len / total_docs) if total_docs else 0.0
    conn.executemany(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        [
            ("num_docs", str(total_docs)),
            ("avg_doc_len", str(avg_doc_len)),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def _has_exact_phrase_from_positions(
    query_terms: list[str],
    positions_by_term: dict[str, list[int]],
) -> bool:
    if not query_terms:
        return False
    if any(term not in positions_by_term for term in query_terms):
        return False

    first_positions = positions_by_term[query_terms[0]]
    for p in first_positions:
        ok = True
        for i, term in enumerate(query_terms[1:], start=1):
            if (p + i) not in positions_by_term[term]:
                ok = False
                break
        if ok:
            return True
    return False


def _proximity_score_from_positions(
    query_terms: list[str],
    positions_by_term: dict[str, list[int]],
    *,
    window: int = 8,
) -> float:
    if len(query_terms) < 2:
        return 0.0
    if any(term not in positions_by_term for term in query_terms):
        return 0.0

    flattened: list[tuple[int, int]] = []
    for i, term in enumerate(query_terms):
        for p in positions_by_term[term]:
            flattened.append((p, i))
    flattened.sort(key=lambda x: x[0])

    need = len(query_terms)
    counts = [0] * need
    covered = 0
    best = None
    left = 0

    for right, (pos_r, idx_r) in enumerate(flattened):
        counts[idx_r] += 1
        if counts[idx_r] == 1:
            covered += 1

        while covered == need and left <= right:
            pos_l, idx_l = flattened[left]
            span = pos_r - pos_l + 1
            if best is None or span < best:
                best = span

            counts[idx_l] -= 1
            if counts[idx_l] == 0:
                covered -= 1
            left += 1

    if best is None:
        return 0.0
    if best <= window:
        return 1.0
    return window / best


def _query_term_coverage(
    query_terms: list[str],
    positions_by_term: dict[str, list[int]],
) -> float:
    unique_query_terms = set(query_terms)
    if not unique_query_terms:
        return 0.0
    covered_terms = sum(1 for term in unique_query_terms if term in positions_by_term)
    return covered_terms / len(unique_query_terms)


def _movie_id_from_passage_id(passage_id: str) -> str:
    return passage_id.rsplit("::", 1)[0]


def _bm25_scores_from_conn(
    conn: sqlite3.Connection,
    qtf: Counter[str],
    *,
    num_docs: int,
    avg_doc_len: float,
    max_postings_per_term: int,
) -> dict[str, float]:
    term_stats: dict[str, tuple[int, float, int]] = {}

    for term, q_weight in qtf.items():
        row = conn.execute(
            "SELECT df FROM term_stats WHERE term = ?",
            (term,),
        ).fetchone()
        if not row:
            continue

        df = int(row[0])
        idf = math.log(1.0 + ((num_docs - df + 0.5) / (df + 0.5)))
        term_stats[term] = (q_weight, idf, df)

    if not term_stats:
        return {}

    seed_terms = _select_bm25_seed_terms(term_stats)
    candidate_scores: defaultdict[str, float] = defaultdict(float)
    average_length = avg_doc_len or 1.0
    for term in seed_terms:
        q_weight, idf, _ = term_stats[term]
        for (passage_id,) in conn.execute(
            """
            SELECT passage_id
            FROM postings
            WHERE term = ?
            LIMIT ?
            """,
            (term, max_postings_per_term),
        ):
            # Candidate seeding only decides which passages deserve full BM25 scoring.
            # Full scoring below applies BM25's term-frequency saturation.
            candidate_scores[passage_id] += idf * q_weight

    if not candidate_scores:
        return {}

    candidate_ids = _top_candidate_ids(candidate_scores, max_candidates=MAX_BM25_CANDIDATES)
    scoring_terms = seed_terms
    term_placeholders = ",".join("?" for _ in scoring_terms)
    chunk_size = max(1, 900 - len(scoring_terms))
    scores: defaultdict[str, float] = defaultdict(float)

    for start in range(0, len(candidate_ids), chunk_size):
        chunk = candidate_ids[start : start + chunk_size]
        passage_placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"""
            SELECT p.term, p.passage_id, p.tf, d.doc_len
            FROM postings p
            JOIN doc_stats d ON d.passage_id = p.passage_id
            WHERE p.term IN ({term_placeholders})
              AND p.passage_id IN ({passage_placeholders})
            """,
            (*scoring_terms, *chunk),
        )

        for term, doc_id, tf, doc_len in rows:
            q_weight, idf, _ = term_stats[term]
            denom = tf + 1.5 * (1 - 0.75 + 0.75 * (doc_len / average_length))
            scores[doc_id] += idf * ((tf * 2.5) / (denom or 1e-9)) * q_weight

    return dict(scores)


def _select_bm25_seed_terms(term_stats: dict[str, tuple[int, float, int]]) -> list[str]:
    terms_by_rarity = sorted(term_stats, key=lambda term: term_stats[term][2])
    seed_terms = [
        term
        for term in terms_by_rarity
        if term_stats[term][2] <= MAX_SEED_TERM_DF
    ][:MAX_SEED_TERMS]
    if seed_terms:
        return seed_terms
    return terms_by_rarity[:FALLBACK_SEED_TERMS]


def _top_candidate_ids(
    candidate_scores: dict[str, float],
    *,
    max_candidates: int,
) -> list[str]:
    if len(candidate_scores) <= max_candidates:
        return list(candidate_scores)
    return [
        passage_id
        for passage_id, _ in heapq.nlargest(
            max_candidates,
            candidate_scores.items(),
            key=lambda item: item[1],
        )
    ]


def _exact_phrase_candidate_ids_from_conn(
    conn: sqlite3.Connection,
    query_terms: list[str],
) -> list[str]:
    if len(query_terms) < 2:
        return []

    unique_query_terms = list(dict.fromkeys(query_terms))
    if len(unique_query_terms) > MAX_EXACT_PHRASE_TERMS:
        return []

    term_stats: dict[str, int] = {}
    for term in unique_query_terms:
        row = conn.execute(
            "SELECT df FROM term_stats WHERE term = ?",
            (term,),
        ).fetchone()
        if row:
            term_stats[term] = int(row[0])

    if not term_stats:
        return []

    rarest_term = min(term_stats, key=lambda term: term_stats[term])
    rows = conn.execute(
        """
        SELECT s.passage_id, p.raw_text
        FROM postings s
        JOIN passages p ON p.passage_id = s.passage_id
        WHERE s.term = ?
        LIMIT ?
        """,
        (rarest_term, MAX_EXACT_PHRASE_SEED_POSTINGS),
    )

    exact_phrase_ids: list[str] = []
    query_term_set = set(query_terms)
    for passage_id, raw_text in rows:
        positions_by_term: dict[str, list[int]] = defaultdict(list)
        for position, term in enumerate(tokenize(raw_text, remove_stopwords=True)):
            if term in query_term_set:
                positions_by_term[term].append(position)
        if _has_exact_phrase_from_positions(query_terms, positions_by_term):
            exact_phrase_ids.append(passage_id)

    return exact_phrase_ids


def _exact_phrase_ids_in_candidates(
    conn: sqlite3.Connection,
    query_terms: list[str],
    candidate_ids: list[str],
) -> list[str]:
    if len(query_terms) < 2 or not candidate_ids:
        return []

    passage_placeholders = ",".join("?" for _ in candidate_ids)
    term_placeholders = ",".join("?" for _ in query_terms)
    rows = conn.execute(
        f"""
        SELECT term, passage_id, positions
        FROM postings
        WHERE term IN ({term_placeholders})
          AND passage_id IN ({passage_placeholders})
        """,
        (*query_terms, *candidate_ids),
    ).fetchall()

    positions_map: dict[str, dict[str, list[int]]] = defaultdict(dict)
    for term, passage_id, positions_json in rows:
        positions_map[passage_id][term] = json.loads(positions_json)

    return [
        passage_id
        for passage_id in candidate_ids
        if _has_exact_phrase_from_positions(query_terms, positions_map.get(passage_id, {}))
    ]


class SQLiteSearchEngine:
    def __init__(
        self,
        db_path: str | Path,
        *,
        authority_index: AuthorityIndex | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.authority_index = (
            authority_index if authority_index is not None else load_default_authority_index()
        )
        # Load metadata once, don't store connection (will create per query)
        temp_conn = _connect(self.db_path)
        self.num_docs = int(self._meta_from_conn(temp_conn, "num_docs", "0"))
        self.avg_doc_len = float(self._meta_from_conn(temp_conn, "avg_doc_len", "0"))
        temp_conn.close()

    @classmethod
    def from_index_dir(cls, index_dir: str | Path) -> "SQLiteSearchEngine":
        return cls(Path(index_dir) / "index.db")

    def _meta_from_conn(self, conn: sqlite3.Connection, key: str, default: str) -> str:
        """Get metadata value from a given connection."""
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        authority_filter: bool = False,
    ) -> list[SearchResult]:
        """Search query using a thread-local database connection."""
        total_started_at = time.perf_counter()
        timing = _QueryTimingLog(query=query, authority_filter=authority_filter)
        conn: sqlite3.Connection | None = None
        try:
            started_at = time.perf_counter()
            conn = _connect(self.db_path)
            timing.record("Open SQLite connection", started_at)
            return self._search_with_conn(
                conn,
                query,
                top_k=top_k,
                authority_filter=authority_filter,
                timing=timing,
            )
        finally:
            if conn is not None:
                started_at = time.perf_counter()
                conn.close()
                timing.record("Close SQLite connection", started_at)
            timing.append(time.perf_counter() - total_started_at)

    def _search_with_conn(
        self,
        conn: sqlite3.Connection,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        authority_filter: bool = False,
        timing: _QueryTimingLog | None = None,
    ) -> list[SearchResult]:
        started_at = time.perf_counter()
        query_terms = tokenize(query, remove_stopwords=True)
        _record_timing(timing, "Tokenize query", started_at)

        started_at = time.perf_counter()
        has_searchable_query = bool(query_terms) and self.num_docs > 0
        _record_timing(timing, "Validate query and index metadata", started_at)
        if not has_searchable_query:
            return []

        started_at = time.perf_counter()
        bm25_scores: dict[str, float] = defaultdict(float)
        qtf = Counter(query_terms)
        _record_timing(timing, "Prepare BM25 query weights", started_at)

        # Limit postings per term to avoid processing millions of documents
        # This makes search responsive even on huge indices
        MAX_POSTINGS_PER_TERM = 40000

        started_at = time.perf_counter()
        bm25_scores = _bm25_scores_from_conn(
            conn,
            qtf,
            num_docs=self.num_docs,
            avg_doc_len=self.avg_doc_len,
            max_postings_per_term=MAX_POSTINGS_PER_TERM,
        )
        _record_timing(timing, "Fetch postings and compute BM25 scores", started_at)

        started_at = time.perf_counter()
        has_bm25_scores = bool(bm25_scores)
        _record_timing(timing, "Validate BM25 candidate scores", started_at)
        if not has_bm25_scores:
            return []

        started_at = time.perf_counter()
        preliminary_rerank_ids = [
            doc_id
            for doc_id, _ in heapq.nlargest(
                RERANK_POOL_SIZE,
                bm25_scores.items(),
                key=lambda x: x[1],
            )
        ]
        exact_phrase_ids = _exact_phrase_ids_in_candidates(
            conn,
            query_terms,
            preliminary_rerank_ids,
        )
        _record_timing(timing, "Check rerank pool for exact phrase candidates", started_at)

        started_at = time.perf_counter()
        has_authoritative_exact = any(
            (
                self.authority_index.multiplier_for_movie_id(
                    _movie_id_from_passage_id(passage_id)
                )
                or 0.0
            )
            >= 1.1
            for passage_id in exact_phrase_ids
        )
        if not has_authoritative_exact:
            recovered_exact_phrase_ids = _exact_phrase_candidate_ids_from_conn(
                conn,
                query_terms,
            )
            exact_phrase_ids = list(
                dict.fromkeys([*exact_phrase_ids, *recovered_exact_phrase_ids])
            )
        if exact_phrase_ids:
            for passage_id in exact_phrase_ids:
                bm25_scores.setdefault(passage_id, 0.0)
        _record_timing(timing, "Recover exact phrase candidates", started_at)

        # Use heapq for efficient top-k selection instead of sorting all docs.

        started_at = time.perf_counter()
        exact_phrase_ids = sorted(
            set(exact_phrase_ids),
            key=lambda passage_id: (
                self.authority_index.multiplier_for_movie_id(
                    _movie_id_from_passage_id(passage_id)
                )
                or 0.0,
                bm25_scores.get(passage_id, 0.0),
            ),
            reverse=True,
        )
        top_k_docs = heapq.nlargest(RERANK_POOL_SIZE, bm25_scores.items(), key=lambda x: x[1])
        rerank_ids = list(
            dict.fromkeys([*exact_phrase_ids, *[doc_id for doc_id, _ in top_k_docs]])
        )[:RERANK_POOL_SIZE]
        _record_timing(timing, "Select rerank candidates", started_at)

        started_at = time.perf_counter()
        # Normalize scores for reranking
        base_scores = dict(minmax_normalize(dict(bm25_scores)))
        _record_timing(timing, "Normalize BM25 scores", started_at)
        if rerank_ids:
            started_at = time.perf_counter()
            ph = ",".join("?" for _ in rerank_ids)
            pt = ",".join("?" for _ in query_terms)
            _record_timing(timing, "Build rerank SQL placeholders", started_at)

            started_at = time.perf_counter()
            positions_map: dict[str, dict[str, list[int]]] = defaultdict(dict)
            rows = conn.execute(
                f"""
                SELECT term, passage_id, positions
                FROM postings
                WHERE term IN ({pt}) AND passage_id IN ({ph})
                """,
                (*query_terms, *rerank_ids),
            ).fetchall()

            for term, doc_id, positions_json in rows:
                positions_map[doc_id][term] = json.loads(positions_json)
            _record_timing(timing, "Fetch and decode rerank term positions", started_at)

            started_at = time.perf_counter()
            passage_rows = conn.execute(
                f"""
                SELECT passage_id, movie_id, source_file, raw_text
                FROM passages
                WHERE passage_id IN ({ph})
                """,
                tuple(rerank_ids),
            ).fetchall()

            passage_map = {row[0]: row for row in passage_rows}
            _record_timing(timing, "Fetch rerank passages", started_at)

            started_at = time.perf_counter()
            for doc_id in rerank_ids:
                info = passage_map.get(doc_id)
                if info is None:
                    continue
                _, _, _, raw_text = info
                pos = positions_map.get(doc_id, {})
                phrase = 1.0 if _has_exact_phrase_from_positions(query_terms, pos) else 0.0
                prox = _proximity_score_from_positions(query_terms, pos)
                coverage = _query_term_coverage(query_terms, pos)
                fuzz = fuzzy_ratio(query, raw_text)
                if phrase:
                    base_scores[doc_id] *= EXACT_PHRASE_BASE_WEIGHT
                authority_phrase_boost = 0.0
                if phrase:
                    multiplier = self.authority_index.multiplier_for_movie_id(info[1])
                    if multiplier is not None:
                        authority_phrase_boost = EXACT_AUTHORITY_BOOST * multiplier
                base_scores[doc_id] += (
                    EXACT_PHRASE_BOOST * phrase
                    + PROXIMITY_BOOST * prox
                    + COVERAGE_BOOST * coverage
                    + FUZZY_BOOST * fuzz
                    + authority_phrase_boost
                )
            _record_timing(timing, "Apply quote-aware rerank scoring", started_at)

        started_at = time.perf_counter()
        if authority_filter:
            for doc_id, score in list(base_scores.items()):
                movie_id = _movie_id_from_passage_id(doc_id)
                multiplier = self.authority_index.multiplier_for_movie_id(movie_id)
                if multiplier is not None:
                    base_scores[doc_id] = score * multiplier
        _record_timing(timing, "Apply authority filter", started_at)

        started_at = time.perf_counter()
        ranked = sorted(base_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        _record_timing(timing, "Sort final scores", started_at)
        if not ranked:
            return []

        started_at = time.perf_counter()
        rid = [doc_id for doc_id, _ in ranked]
        ph = ",".join("?" for _ in rid)
        rows = conn.execute(
            f"""
            SELECT passage_id, movie_id, source_file, raw_text
            FROM passages
            WHERE passage_id IN ({ph})
            """,
            tuple(rid),
        ).fetchall()
        info = {row[0]: row for row in rows}
        _record_timing(timing, "Fetch final result passages", started_at)

        started_at = time.perf_counter()
        results: list[SearchResult] = []
        for doc_id, score in ranked:
            row = info.get(doc_id)
            if row is None:
                continue
            _, movie_id, source_file, raw_text = row
            snippet = raw_text[:220] + ("..." if len(raw_text) > 220 else "")
            results.append(
                SearchResult(
                    passage_id=doc_id,
                    movie_id=movie_id,
                    score=float(score),
                    snippet=snippet,
                    source_file=source_file,
                )
            )

        _record_timing(timing, "Build SearchResult objects", started_at)
        return results
