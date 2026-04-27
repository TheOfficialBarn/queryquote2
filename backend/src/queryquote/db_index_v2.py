"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
SQLite v2 index builder and search engine for QueryQuote transcript experiments.

Last updated: 2026-04-27 - Added relaxed content-phrase scoring to the default
v2 reranker so source passages survive small wording and stopword differences.
"""

from __future__ import annotations

import csv
import heapq
import json
import math
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .analyzer_v2 import full_tokenize_v2, is_bm25_term
from .authority import (
    authority_multiplier,
    normalize_title,
    parse_release_year,
    parse_title_year,
    parse_vote_count,
    split_movie_id,
)
from .config import DEFAULT_MAX_PASSAGE_TOKENS, DEFAULT_PASSAGE_OVERLAP, DEFAULT_TOP_K
from .passages import iter_transcript_files, movie_id_from_filename
from .quote_matching import fuzzy_ratio
from .ranking import minmax_normalize
from .types import SearchResult


DEFAULT_AUTHORITY_COMPACT_CSV_PATH = Path(__file__).resolve().parents[2] / "authority_compact.csv"
DEFAULT_TIMING_LOG_PATH_V2 = Path(__file__).resolve().parents[3] / "test" / "time-logs" / "times-v2.txt"
SCHEMA_VERSION = "2"
CORPUS_MODES = ("all", "intersection", "rest")
_ARTICLES = {"a", "an", "the"}
MAX_BM25_CANDIDATES = 10000
RERANK_POOL_SIZE = 500
MAX_SEED_TERMS = 8
MAX_SEED_TERM_DF = 250000
MAX_POSTINGS_PER_TERM = 40000
MAX_EXACT_PHRASE_SEED_POSTINGS = 120000
MAX_EXACT_PHRASE_TERMS = 12
FALLBACK_SEED_TERMS = 3
EXACT_PHRASE_BOOST = 1.85
EXACT_PHRASE_BASE_WEIGHT = 0.10
RELAXED_PHRASE_BOOST = 1.05
RELAXED_PROXIMITY_BOOST = 0.45
RELAXED_COVERAGE_BOOST = 0.15
PROXIMITY_BOOST = 0.55
COVERAGE_BOOST = 0.20
FUZZY_BOOST = 0.15
EXACT_AUTHORITY_BOOST = 0.35


@dataclass(frozen=True, slots=True)
class _AuthorityRecord:
    title: str
    year: str | None
    rating: float | None
    votes: int | None
    genres: str
    multiplier: float | None


@dataclass(frozen=True, slots=True)
class _AuthorityMatch:
    record: _AuthorityRecord
    match_type: str
    year_relation: str


@dataclass(slots=True)
class _QueryTimingLogV2:
    query: str
    authority_filter: bool = False
    log_path: Path = DEFAULT_TIMING_LOG_PATH_V2
    metrics: list[tuple[str, float]] = field(default_factory=list)

    def record(self, label: str, started_at: float) -> None:
        self.metrics.append((label, time.perf_counter() - started_at))

    def append(self, total_seconds: float) -> None:
        authority_label = "On" if self.authority_filter else "Off"
        lines = [f'Query: "{self.query}" | Authority Boost: {authority_label} | Index: v2']
        lines.extend(f"{label}: {duration:.6f}s" for label, duration in self.metrics)
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
            # Query serving should not fail because local diagnostics are unavailable.
            return


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -200000")
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS movies (
            movie_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            year TEXT,
            source_file TEXT NOT NULL,
            authority_title TEXT,
            authority_year TEXT,
            authority_rating REAL,
            authority_votes INTEGER,
            authority_genres TEXT,
            authority_multiplier REAL,
            authority_match_type TEXT,
            authority_year_relation TEXT,
            corpus_tier TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS passages (
            passage_id TEXT PRIMARY KEY,
            movie_id TEXT NOT NULL,
            source_file TEXT NOT NULL,
            token_start INTEGER NOT NULL,
            token_end INTEGER NOT NULL,
            text TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS passage_stats (
            passage_id TEXT PRIMARY KEY,
            bm25_len INTEGER NOT NULL,
            full_len INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bm25_postings (
            term TEXT NOT NULL,
            passage_id TEXT NOT NULL,
            tf INTEGER NOT NULL,
            positions TEXT NOT NULL,
            PRIMARY KEY (term, passage_id)
        );

        CREATE TABLE IF NOT EXISTS bm25_term_stats (
            term TEXT PRIMARY KEY,
            df INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS movie_phrase_postings (
            term TEXT NOT NULL,
            movie_id TEXT NOT NULL,
            tf INTEGER NOT NULL,
            positions TEXT NOT NULL,
            PRIMARY KEY (term, movie_id)
        );

        CREATE TABLE IF NOT EXISTS movie_phrase_term_stats (
            term TEXT PRIMARY KEY,
            df INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_passages_movie_window
            ON passages(movie_id, token_start, token_end);
        CREATE INDEX IF NOT EXISTS idx_bm25_postings_passage
            ON bm25_postings(passage_id);
        CREATE INDEX IF NOT EXISTS idx_movie_phrase_postings_movie
            ON movie_phrase_postings(movie_id);
        CREATE INDEX IF NOT EXISTS idx_movies_authority
            ON movies(authority_match_type, authority_year_relation, authority_votes);
        CREATE INDEX IF NOT EXISTS idx_movies_corpus_tier
            ON movies(corpus_tier);
        """
    )


def build_sqlite_index_v2(
    *,
    data_dir: str | Path,
    output_dir: str | Path,
    authority_csv_path: str | Path | None = None,
    max_passage_tokens: int = DEFAULT_MAX_PASSAGE_TOKENS,
    passage_overlap: int = DEFAULT_PASSAGE_OVERLAP,
    progress_every_files: int = 1000,
    batch_size: int = 50000,
    corpus_mode: str = "all",
) -> Path:
    """Build the v2 index in a separate output directory."""
    if max_passage_tokens <= 0:
        raise ValueError("max_passage_tokens must be > 0")
    if passage_overlap < 0 or passage_overlap >= max_passage_tokens:
        raise ValueError("passage_overlap must satisfy 0 <= overlap < max_passage_tokens")
    if progress_every_files <= 0:
        raise ValueError("progress_every_files must be > 0")
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    if corpus_mode not in CORPUS_MODES:
        allowed = ", ".join(CORPUS_MODES)
        raise ValueError(f"corpus_mode must be one of: {allowed}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "index.db"
    if db_path.exists():
        db_path.unlink()

    authority_path = (
        Path(authority_csv_path)
        if authority_csv_path is not None
        else DEFAULT_AUTHORITY_COMPACT_CSV_PATH
    )
    authority_index = _load_authority_records(authority_path)
    transcript_files = list(iter_transcript_files(data_dir))
    total_source_files = len(transcript_files)

    conn = _connect(db_path)
    _create_schema(conn)

    bm25_df: Counter[str] = Counter()
    movie_phrase_df: Counter[str] = Counter()
    passage_rows: list[tuple[str, str, str, int, int, str]] = []
    passage_stat_rows: list[tuple[str, int, int]] = []
    bm25_posting_rows: list[tuple[str, str, int, str]] = []
    movie_rows: list[tuple[object, ...]] = []
    movie_phrase_rows: list[tuple[str, str, int, str]] = []

    files_seen = 0
    movies_skipped = 0
    movies_indexed = 0
    passages_indexed = 0
    total_bm25_len = 0
    total_full_len = 0
    started_at = time.time()

    for file_path in transcript_files:
        files_seen += 1
        movie_id = movie_id_from_filename(Path(file_path).name)
        title, year = split_movie_id(movie_id)
        authority_match = _match_authority_record(title, year, authority_index)
        corpus_tier = "intersection" if authority_match is not None else "rest"
        if corpus_mode != "all" and corpus_tier != corpus_mode:
            movies_skipped += 1
            if files_seen % progress_every_files == 0:
                _print_progress(
                    files_seen=files_seen,
                    total_files=total_source_files,
                    movies_indexed=movies_indexed,
                    movies_skipped=movies_skipped,
                    passages_indexed=passages_indexed,
                    started_at=started_at,
                    corpus_mode=corpus_mode,
                )
            continue

        raw_text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        full_tokens = full_tokenize_v2(raw_text)
        if not full_tokens:
            movies_skipped += 1
            continue

        movie_rows.append(
            _movie_row(
                movie_id=movie_id,
                title=title,
                year=year,
                source_file=str(file_path),
                authority_match=authority_match,
                corpus_tier=corpus_tier,
            )
        )
        movies_indexed += 1
        total_full_len += len(full_tokens)

        movie_positions = _positions_by_term(full_tokens)
        for term, positions in movie_positions.items():
            movie_phrase_df[term] += 1
            movie_phrase_rows.append(
                (term, movie_id, len(positions), _dump_positions(positions))
            )

        step = max_passage_tokens - passage_overlap
        for passage_number, start in enumerate(range(0, len(full_tokens), step)):
            chunk = full_tokens[start : start + max_passage_tokens]
            if not chunk:
                break

            passage_id = f"{movie_id}::p{passage_number:04d}"
            passage_text = " ".join(chunk)
            token_end = start + len(chunk)
            bm25_positions = _bm25_positions_by_term(chunk)
            bm25_len = sum(len(positions) for positions in bm25_positions.values())

            passage_rows.append(
                (passage_id, movie_id, str(file_path), start, token_end, passage_text)
            )
            passage_stat_rows.append((passage_id, bm25_len, len(chunk)))
            passages_indexed += 1
            total_bm25_len += bm25_len

            for term, positions in bm25_positions.items():
                bm25_df[term] += 1
                bm25_posting_rows.append(
                    (term, passage_id, len(positions), _dump_positions(positions))
                )

            if start + max_passage_tokens >= len(full_tokens):
                break

        if (
            len(bm25_posting_rows) >= batch_size
            or len(movie_phrase_rows) >= batch_size
            or files_seen % progress_every_files == 0
        ):
            _flush_index_rows(
                conn,
                movie_rows,
                passage_rows,
                passage_stat_rows,
                bm25_posting_rows,
                movie_phrase_rows,
            )
            movie_rows.clear()
            passage_rows.clear()
            passage_stat_rows.clear()
            bm25_posting_rows.clear()
            movie_phrase_rows.clear()

        if files_seen % progress_every_files == 0:
            _print_progress(
                files_seen=files_seen,
                total_files=total_source_files,
                movies_indexed=movies_indexed,
                movies_skipped=movies_skipped,
                passages_indexed=passages_indexed,
                started_at=started_at,
                corpus_mode=corpus_mode,
            )

    _flush_index_rows(
        conn,
        movie_rows,
        passage_rows,
        passage_stat_rows,
        bm25_posting_rows,
        movie_phrase_rows,
    )

    conn.executemany(
        "INSERT OR REPLACE INTO bm25_term_stats(term, df) VALUES (?, ?)",
        bm25_df.items(),
    )
    conn.executemany(
        "INSERT OR REPLACE INTO movie_phrase_term_stats(term, df) VALUES (?, ?)",
        movie_phrase_df.items(),
    )

    avg_bm25_len = (total_bm25_len / passages_indexed) if passages_indexed else 0.0
    avg_full_movie_len = (total_full_len / movies_indexed) if movies_indexed else 0.0
    conn.executemany(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        [
            ("schema_version", SCHEMA_VERSION),
            ("num_movies", str(movies_indexed)),
            ("num_passages", str(passages_indexed)),
            ("avg_bm25_passage_len", str(avg_bm25_len)),
            ("avg_full_movie_len", str(avg_full_movie_len)),
            ("max_passage_tokens", str(max_passage_tokens)),
            ("passage_overlap", str(passage_overlap)),
            ("authority_csv_path", str(authority_path)),
            ("corpus_mode", corpus_mode),
            ("total_source_files", str(total_source_files)),
            ("movies_skipped", str(movies_skipped)),
        ],
    )
    conn.commit()
    conn.execute("PRAGMA optimize")
    conn.close()
    return db_path


def _flush_index_rows(
    conn: sqlite3.Connection,
    movie_rows: list[tuple[object, ...]],
    passage_rows: list[tuple[str, str, str, int, int, str]],
    passage_stat_rows: list[tuple[str, int, int]],
    bm25_posting_rows: list[tuple[str, str, int, str]],
    movie_phrase_rows: list[tuple[str, str, int, str]],
) -> None:
    if movie_rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO movies(
                movie_id,
                title,
                year,
                source_file,
                authority_title,
                authority_year,
                authority_rating,
                authority_votes,
                authority_genres,
                authority_multiplier,
                authority_match_type,
                authority_year_relation,
                corpus_tier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            movie_rows,
        )
    if passage_rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO passages(
                passage_id,
                movie_id,
                source_file,
                token_start,
                token_end,
                text
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            passage_rows,
        )
    if passage_stat_rows:
        conn.executemany(
            "INSERT OR REPLACE INTO passage_stats(passage_id, bm25_len, full_len) VALUES (?, ?, ?)",
            passage_stat_rows,
        )
    if bm25_posting_rows:
        conn.executemany(
            "INSERT OR REPLACE INTO bm25_postings(term, passage_id, tf, positions) VALUES (?, ?, ?, ?)",
            bm25_posting_rows,
        )
    if movie_phrase_rows:
        conn.executemany(
            "INSERT OR REPLACE INTO movie_phrase_postings(term, movie_id, tf, positions) VALUES (?, ?, ?, ?)",
            movie_phrase_rows,
        )
    if any((movie_rows, passage_rows, passage_stat_rows, bm25_posting_rows, movie_phrase_rows)):
        conn.commit()


def _positions_by_term(tokens: list[str]) -> dict[str, list[int]]:
    positions: dict[str, list[int]] = defaultdict(list)
    for position, term in enumerate(tokens):
        positions[term].append(position)
    return positions


def _bm25_positions_by_term(tokens: list[str]) -> dict[str, list[int]]:
    positions: dict[str, list[int]] = defaultdict(list)
    for position, term in enumerate(tokens):
        if is_bm25_term(term):
            positions[term].append(position)
    return positions


def _dump_positions(positions: list[int]) -> str:
    return json.dumps(positions, separators=(",", ":"))


def _load_authority_records(
    csv_path: Path,
) -> dict[tuple[str, str], list[_AuthorityRecord]]:
    if not csv_path.exists():
        return {}

    raw_rows: list[dict[str, str]] = []
    max_votes = 0
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = (row.get("Title") or "").strip()
            if not title:
                continue
            raw_rows.append(row)
            votes = parse_vote_count(row.get("No of Persons Voted"))
            if votes is not None:
                max_votes = max(max_votes, votes)

    records_by_key: dict[tuple[str, str], list[_AuthorityRecord]] = defaultdict(list)
    for row in raw_rows:
        title = (row.get("Title") or "").strip()
        votes = parse_vote_count(row.get("No of Persons Voted"))
        record = _AuthorityRecord(
            title=title,
            year=parse_title_year(title) or parse_release_year(row.get("Release Date")),
            rating=_parse_float(row.get("Rating")),
            votes=votes,
            genres=(row.get("Genres") or "").strip(),
            multiplier=authority_multiplier(votes, max_votes=max_votes)
            if votes is not None and max_votes > 0
            else None,
        )
        for key in _loose_title_keys(title):
            records_by_key[key].append(record)

    return records_by_key


def _match_authority_record(
    title: str,
    year: str | None,
    records_by_key: dict[tuple[str, str], list[_AuthorityRecord]],
) -> _AuthorityMatch | None:
    candidates: list[tuple[int, int, str, _AuthorityRecord]] = []
    for match_type, key in _loose_title_keys(title):
        for record in records_by_key.get((match_type, key), []):
            year_relation = _year_relation(year, record.year)
            year_score = 2 if year_relation == "same_year" else 1
            votes = record.votes or 0
            candidates.append((year_score, votes, match_type, record))

    if not candidates:
        return None

    year_score, _, match_type, record = max(candidates, key=lambda item: item[:2])
    return _AuthorityMatch(
        record=record,
        match_type=match_type,
        year_relation="same_year" if year_score == 2 else _year_relation(year, record.year),
    )


def _movie_row(
    *,
    movie_id: str,
    title: str,
    year: str | None,
    source_file: str,
    authority_match: _AuthorityMatch | None,
    corpus_tier: str,
) -> tuple[object, ...]:
    if authority_match is None:
        return (
            movie_id,
            title,
            year,
            source_file,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            corpus_tier,
        )

    record = authority_match.record
    return (
        movie_id,
        title,
        year,
        source_file,
        record.title,
        record.year,
        record.rating,
        record.votes,
        record.genres,
        record.multiplier,
        authority_match.match_type,
        authority_match.year_relation,
        corpus_tier,
    )


def _print_progress(
    *,
    files_seen: int,
    total_files: int,
    movies_indexed: int,
    movies_skipped: int,
    passages_indexed: int,
    started_at: float,
    corpus_mode: str,
) -> None:
    elapsed = time.time() - started_at
    files_remaining = max(0, total_files - files_seen)
    seconds_per_file = elapsed / files_seen if files_seen else 0.0
    eta_seconds = files_remaining * seconds_per_file
    print(
        "[build-v2] "
        f"mode={corpus_mode} files={files_seen}/{total_files} "
        f"movies={movies_indexed} skipped={movies_skipped} passages={passages_indexed} "
        f"elapsed={_format_seconds(elapsed)} eta={_format_seconds(eta_seconds)}"
    )


def _format_seconds(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _loose_title_keys(title: str) -> set[tuple[str, str]]:
    normalized = normalize_title(title)
    if not normalized:
        return set()

    keys = {("normalized", normalized)}
    parts = normalized.split()
    if len(parts) > 1 and parts[0] in _ARTICLES:
        keys.add(("without_leading_article", " ".join(parts[1:])))
    return keys


def _year_relation(left: str | None, right: str | None) -> str:
    if left and right:
        return "same_year" if left == right else "different_year"
    if left or right:
        return "one_year_missing"
    return "both_year_missing"


def _parse_float(value: str | None) -> float | None:
    clean = (value or "").strip()
    if not clean:
        return None
    try:
        return float(clean)
    except ValueError:
        return None


def _record_timing_v2(
    timing: _QueryTimingLogV2 | None,
    label: str,
    started_at: float,
) -> None:
    if timing is not None:
        timing.record(label, started_at)


def _has_exact_phrase_from_positions(
    query_terms: list[str],
    positions_by_term: dict[str, list[int]],
) -> bool:
    return bool(_exact_phrase_starts_from_positions(query_terms, positions_by_term))


def _exact_phrase_starts_from_positions(
    query_terms: list[str],
    positions_by_term: dict[str, list[int]],
) -> list[int]:
    if not query_terms:
        return []
    if any(term not in positions_by_term for term in query_terms):
        return []

    starts: list[int] = []
    for position in positions_by_term[query_terms[0]]:
        if all(
            (position + offset) in positions_by_term[term]
            for offset, term in enumerate(query_terms[1:], start=1)
        ):
            starts.append(position)
    return starts


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
    for index, term in enumerate(query_terms):
        for position in positions_by_term[term]:
            flattened.append((position, index))
    flattened.sort(key=lambda item: item[0])

    needed = len(query_terms)
    counts = [0] * needed
    covered = 0
    best_span: int | None = None
    left = 0

    for right, (right_position, right_index) in enumerate(flattened):
        counts[right_index] += 1
        if counts[right_index] == 1:
            covered += 1

        while covered == needed and left <= right:
            left_position, left_index = flattened[left]
            span = right_position - left_position + 1
            if best_span is None or span < best_span:
                best_span = span

            counts[left_index] -= 1
            if counts[left_index] == 0:
                covered -= 1
            left += 1

    if best_span is None:
        return 0.0
    if best_span <= window:
        return 1.0
    return window / best_span


def _ordered_proximity_score_from_positions(
    query_terms: list[str],
    positions_by_term: dict[str, list[int]],
    *,
    window: int = 12,
) -> float:
    if len(query_terms) < 2:
        return 0.0
    if any(term not in positions_by_term for term in query_terms):
        return 0.0

    best_span: int | None = None
    for start_position in positions_by_term[query_terms[0]]:
        current_position = start_position
        matched = True
        for term in query_terms[1:]:
            next_position = _first_position_after(
                positions_by_term[term],
                current_position,
            )
            if next_position is None:
                matched = False
                break
            current_position = next_position

        if not matched:
            continue

        span = current_position - start_position + 1
        if best_span is None or span < best_span:
            best_span = span

    if best_span is None:
        return 0.0

    ideal_span = len(query_terms)
    if best_span <= ideal_span:
        return 1.0
    if best_span <= window:
        return ideal_span / best_span
    return window / best_span


def _first_position_after(positions: list[int], current_position: int) -> int | None:
    for position in positions:
        if position > current_position:
            return position
    return None


def _query_term_coverage(
    query_terms: list[str],
    positions_by_term: dict[str, list[int]],
) -> float:
    unique_query_terms = set(query_terms)
    if not unique_query_terms:
        return 0.0
    covered_terms = sum(1 for term in unique_query_terms if term in positions_by_term)
    return covered_terms / len(unique_query_terms)


def _positions_from_tokens(tokens: list[str], terms: set[str]) -> dict[str, list[int]]:
    positions: dict[str, list[int]] = defaultdict(list)
    for position, term in enumerate(tokens):
        if term in terms:
            positions[term].append(position)
    return positions


def _content_terms_from_tokens(tokens: list[str]) -> list[str]:
    return [term for term in tokens if is_bm25_term(term)]


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


def _bm25_scores_from_conn(
    conn: sqlite3.Connection,
    qtf: Counter[str],
    *,
    num_passages: int,
    avg_bm25_len: float,
) -> dict[str, float]:
    term_stats: dict[str, tuple[int, float, int]] = {}
    for term, q_weight in qtf.items():
        row = conn.execute(
            "SELECT df FROM bm25_term_stats WHERE term = ?",
            (term,),
        ).fetchone()
        if not row:
            continue

        df = int(row[0])
        idf = math.log(1.0 + ((num_passages - df + 0.5) / (df + 0.5)))
        term_stats[term] = (q_weight, idf, df)

    if not term_stats:
        return {}

    seed_terms = _select_bm25_seed_terms(term_stats)
    candidate_scores: defaultdict[str, float] = defaultdict(float)
    average_length = avg_bm25_len or 1.0

    for term in seed_terms:
        q_weight, idf, _ = term_stats[term]
        for (passage_id,) in conn.execute(
            """
            SELECT passage_id
            FROM bm25_postings
            WHERE term = ?
            LIMIT ?
            """,
            (term, MAX_POSTINGS_PER_TERM),
        ):
            candidate_scores[passage_id] += idf * q_weight

    if not candidate_scores:
        return {}

    candidate_ids = _top_candidate_ids(
        candidate_scores,
        max_candidates=MAX_BM25_CANDIDATES,
    )
    scoring_terms = seed_terms
    term_placeholders = ",".join("?" for _ in scoring_terms)
    chunk_size = max(1, 900 - len(scoring_terms))
    scores: defaultdict[str, float] = defaultdict(float)

    for start in range(0, len(candidate_ids), chunk_size):
        chunk = candidate_ids[start : start + chunk_size]
        passage_placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"""
            SELECT p.term, p.passage_id, p.tf, s.bm25_len
            FROM bm25_postings p
            JOIN passage_stats s ON s.passage_id = p.passage_id
            WHERE p.term IN ({term_placeholders})
              AND p.passage_id IN ({passage_placeholders})
            """,
            (*scoring_terms, *chunk),
        )

        for term, passage_id, term_frequency, bm25_len in rows:
            q_weight, idf, _ = term_stats[term]
            denominator = term_frequency + 1.5 * (
                1 - 0.75 + 0.75 * (bm25_len / average_length)
            )
            scores[passage_id] += (
                idf
                * ((term_frequency * 2.5) / (denominator or 1e-9))
                * q_weight
            )

    return dict(scores)


def _chunked(values: list[str], size: int = 400) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _exact_phrase_passage_ids_from_movie_positions(
    conn: sqlite3.Connection,
    query_terms: list[str],
) -> list[str]:
    if len(query_terms) < 2:
        return []

    unique_query_terms = list(dict.fromkeys(query_terms))
    if len(unique_query_terms) > MAX_EXACT_PHRASE_TERMS:
        return []

    term_dfs: dict[str, int] = {}
    for term in unique_query_terms:
        row = conn.execute(
            "SELECT df FROM movie_phrase_term_stats WHERE term = ?",
            (term,),
        ).fetchone()
        if row:
            term_dfs[term] = int(row[0])

    if len(term_dfs) != len(unique_query_terms):
        return []

    rarest_term = min(term_dfs, key=lambda term: term_dfs[term])
    seed_rows = conn.execute(
        """
        SELECT movie_id
        FROM movie_phrase_postings
        WHERE term = ?
        LIMIT ?
        """,
        (rarest_term, MAX_EXACT_PHRASE_SEED_POSTINGS),
    ).fetchall()
    movie_ids = [row[0] for row in seed_rows]
    if not movie_ids:
        return []

    phrase_hits_by_movie: dict[str, list[int]] = {}
    term_placeholders = ",".join("?" for _ in unique_query_terms)
    for movie_chunk in _chunked(movie_ids):
        movie_placeholders = ",".join("?" for _ in movie_chunk)
        rows = conn.execute(
            f"""
            SELECT term, movie_id, positions
            FROM movie_phrase_postings
            WHERE term IN ({term_placeholders})
              AND movie_id IN ({movie_placeholders})
            """,
            (*unique_query_terms, *movie_chunk),
        )

        positions_by_movie: dict[str, dict[str, list[int]]] = defaultdict(dict)
        for term, movie_id, positions_json in rows:
            positions_by_movie[movie_id][term] = json.loads(positions_json)

        for movie_id, positions_by_term in positions_by_movie.items():
            starts = _exact_phrase_starts_from_positions(query_terms, positions_by_term)
            if starts:
                phrase_hits_by_movie[movie_id] = starts

    if not phrase_hits_by_movie:
        return []

    passage_ids: list[str] = []
    phrase_len = len(query_terms)
    for movie_id, starts in phrase_hits_by_movie.items():
        for phrase_start in starts:
            phrase_end = phrase_start + phrase_len
            rows = conn.execute(
                """
                SELECT passage_id
                FROM passages
                WHERE movie_id = ?
                  AND token_start <= ?
                  AND token_end >= ?
                """,
                (movie_id, phrase_start, phrase_end),
            ).fetchall()
            passage_ids.extend(row[0] for row in rows)

    return list(dict.fromkeys(passage_ids))


def _authority_multipliers_from_conn(
    conn: sqlite3.Connection,
    movie_ids: list[str],
) -> dict[str, float | None]:
    if not movie_ids:
        return {}

    multipliers: dict[str, float | None] = {}
    for movie_chunk in _chunked(movie_ids):
        placeholders = ",".join("?" for _ in movie_chunk)
        rows = conn.execute(
            f"""
            SELECT movie_id, authority_multiplier
            FROM movies
            WHERE movie_id IN ({placeholders})
            """,
            tuple(movie_chunk),
        )
        multipliers.update({movie_id: multiplier for movie_id, multiplier in rows})
    return multipliers


class SQLiteSearchEngineV2:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        conn = _connect(self.db_path)
        self.schema_version = self._meta_from_conn(conn, "schema_version", "")
        self.num_passages = int(self._meta_from_conn(conn, "num_passages", "0"))
        self.avg_bm25_len = float(self._meta_from_conn(conn, "avg_bm25_passage_len", "0"))
        self.corpus_mode = self._meta_from_conn(conn, "corpus_mode", "unknown")
        conn.close()

        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Expected v2 SQLite schema {SCHEMA_VERSION}, got {self.schema_version or 'missing'}"
            )

    @classmethod
    def from_index_dir(cls, index_dir: str | Path) -> "SQLiteSearchEngineV2":
        return cls(Path(index_dir) / "index.db")

    def _meta_from_conn(self, conn: sqlite3.Connection, key: str, default: str) -> str:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        authority_filter: bool = False,
    ) -> list[SearchResult]:
        total_started_at = time.perf_counter()
        timing = _QueryTimingLogV2(query=query, authority_filter=authority_filter)
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
        top_k: int,
        authority_filter: bool,
        timing: _QueryTimingLogV2 | None = None,
    ) -> list[SearchResult]:
        started_at = time.perf_counter()
        query_full_terms = full_tokenize_v2(query)
        query_bm25_terms = [term for term in query_full_terms if is_bm25_term(term)]
        query_relaxed_terms = _content_terms_from_tokens(query_full_terms)
        _record_timing_v2(timing, "Tokenize query", started_at)

        started_at = time.perf_counter()
        if not query_full_terms or self.num_passages <= 0:
            return []
        qtf = Counter(query_bm25_terms)
        _record_timing_v2(timing, "Prepare BM25 query weights", started_at)

        started_at = time.perf_counter()
        bm25_scores = (
            _bm25_scores_from_conn(
                conn,
                qtf,
                num_passages=self.num_passages,
                avg_bm25_len=self.avg_bm25_len,
            )
            if qtf
            else {}
        )
        _record_timing_v2(timing, "Fetch postings and compute BM25 scores", started_at)

        started_at = time.perf_counter()
        preliminary_rerank_ids = [
            passage_id
            for passage_id, _ in heapq.nlargest(
                RERANK_POOL_SIZE,
                bm25_scores.items(),
                key=lambda item: item[1],
            )
        ]
        exact_phrase_ids = self._exact_phrase_ids_in_candidate_texts(
            conn,
            query_full_terms,
            preliminary_rerank_ids,
        )
        recovered_exact_phrase_ids = _exact_phrase_passage_ids_from_movie_positions(
            conn,
            query_full_terms,
        )
        exact_phrase_ids = list(
            dict.fromkeys([*exact_phrase_ids, *recovered_exact_phrase_ids])
        )
        for passage_id in exact_phrase_ids:
            bm25_scores.setdefault(passage_id, 0.0)
        _record_timing_v2(timing, "Recover exact phrase candidates", started_at)

        if not bm25_scores:
            return []

        started_at = time.perf_counter()
        base_scores = dict(minmax_normalize(dict(bm25_scores)))
        exact_phrase_ids = sorted(
            set(exact_phrase_ids),
            key=lambda passage_id: bm25_scores.get(passage_id, 0.0),
            reverse=True,
        )
        top_candidate_docs = heapq.nlargest(
            RERANK_POOL_SIZE,
            bm25_scores.items(),
            key=lambda item: item[1],
        )
        rerank_ids = list(
            dict.fromkeys([*exact_phrase_ids, *[doc_id for doc_id, _ in top_candidate_docs]])
        )[:RERANK_POOL_SIZE]
        _record_timing_v2(timing, "Select rerank candidates", started_at)

        started_at = time.perf_counter()
        passage_map = self._passages_by_id(conn, rerank_ids)
        movie_ids = list({row[1] for row in passage_map.values()})
        authority_multipliers = _authority_multipliers_from_conn(conn, movie_ids)
        query_term_set = set(query_full_terms)
        _record_timing_v2(timing, "Fetch rerank passages and authority", started_at)

        started_at = time.perf_counter()
        for passage_id in rerank_ids:
            info = passage_map.get(passage_id)
            if info is None:
                continue

            _, movie_id, _, text = info
            passage_tokens = full_tokenize_v2(text)
            positions = _positions_from_tokens(passage_tokens, query_term_set)
            phrase = (
                1.0
                if _has_exact_phrase_from_positions(query_full_terms, positions)
                else 0.0
            )
            proximity = _proximity_score_from_positions(query_full_terms, positions)
            coverage = _query_term_coverage(query_full_terms, positions)
            relaxed_phrase = 0.0
            relaxed_proximity = 0.0
            relaxed_coverage = 0.0
            if query_relaxed_terms:
                passage_content_terms = _content_terms_from_tokens(passage_tokens)
                relaxed_positions = _positions_from_tokens(
                    passage_content_terms,
                    set(query_relaxed_terms),
                )
                relaxed_phrase = (
                    1.0
                    if _has_exact_phrase_from_positions(
                        query_relaxed_terms,
                        relaxed_positions,
                    )
                    else 0.0
                )
                relaxed_proximity = _ordered_proximity_score_from_positions(
                    query_relaxed_terms,
                    relaxed_positions,
                )
                relaxed_coverage = _query_term_coverage(
                    query_relaxed_terms,
                    relaxed_positions,
                )
            fuzz = fuzzy_ratio(query, text)

            if phrase:
                base_scores[passage_id] *= EXACT_PHRASE_BASE_WEIGHT

            authority_phrase_boost = 0.0
            multiplier = authority_multipliers.get(movie_id)
            if phrase and multiplier is not None:
                authority_phrase_boost = EXACT_AUTHORITY_BOOST * multiplier

            base_scores[passage_id] += (
                EXACT_PHRASE_BOOST * phrase
                + RELAXED_PHRASE_BOOST * relaxed_phrase
                + RELAXED_PROXIMITY_BOOST * relaxed_proximity
                + RELAXED_COVERAGE_BOOST * relaxed_coverage
                + PROXIMITY_BOOST * proximity
                + COVERAGE_BOOST * coverage
                + FUZZY_BOOST * fuzz
                + authority_phrase_boost
            )
        _record_timing_v2(timing, "Apply quote-aware rerank scoring", started_at)

        started_at = time.perf_counter()
        if authority_filter:
            for passage_id, score in list(base_scores.items()):
                info = passage_map.get(passage_id)
                if info is None:
                    continue
                multiplier = authority_multipliers.get(info[1])
                if multiplier is not None:
                    base_scores[passage_id] = score * multiplier
        _record_timing_v2(timing, "Apply authority filter", started_at)

        started_at = time.perf_counter()
        ranked = sorted(base_scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        _record_timing_v2(timing, "Sort final scores", started_at)
        if not ranked:
            return []

        started_at = time.perf_counter()
        final_passage_map = self._passages_by_id(conn, [passage_id for passage_id, _ in ranked])
        _record_timing_v2(timing, "Fetch final result passages", started_at)

        started_at = time.perf_counter()
        results: list[SearchResult] = []
        for passage_id, score in ranked:
            row = final_passage_map.get(passage_id)
            if row is None:
                continue
            _, movie_id, source_file, text = row
            snippet = text[:220] + ("..." if len(text) > 220 else "")
            results.append(
                SearchResult(
                    passage_id=passage_id,
                    movie_id=movie_id,
                    score=float(score),
                    snippet=snippet,
                    source_file=source_file,
                )
            )
        _record_timing_v2(timing, "Build SearchResult objects", started_at)
        return results

    def _exact_phrase_ids_in_candidate_texts(
        self,
        conn: sqlite3.Connection,
        query_terms: list[str],
        candidate_ids: list[str],
    ) -> list[str]:
        if len(query_terms) < 2 or not candidate_ids:
            return []

        term_set = set(query_terms)
        exact_ids: list[str] = []
        for passage_id, _, _, text in self._passages_by_id(conn, candidate_ids).values():
            positions = _positions_from_tokens(full_tokenize_v2(text), term_set)
            if _has_exact_phrase_from_positions(query_terms, positions):
                exact_ids.append(passage_id)
        return exact_ids

    def _passages_by_id(
        self,
        conn: sqlite3.Connection,
        passage_ids: list[str],
    ) -> dict[str, tuple[str, str, str, str]]:
        if not passage_ids:
            return {}

        passages: dict[str, tuple[str, str, str, str]] = {}
        for passage_chunk in _chunked(passage_ids):
            placeholders = ",".join("?" for _ in passage_chunk)
            rows = conn.execute(
                f"""
                SELECT passage_id, movie_id, source_file, text
                FROM passages
                WHERE passage_id IN ({placeholders})
                """,
                tuple(passage_chunk),
            ).fetchall()
            passages.update({row[0]: row for row in rows})
        return passages
