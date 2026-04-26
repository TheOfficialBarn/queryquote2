"""Prologue:
SQLite v2 index builder for QueryQuote transcript search experiments.
Last updated: 2026-04-26 - Adds intersection/rest corpus modes with ETA
progress while preserving separate v2 indexes and legacy index compatibility.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
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
from .config import DEFAULT_MAX_PASSAGE_TOKENS, DEFAULT_PASSAGE_OVERLAP
from .passages import iter_transcript_files, movie_id_from_filename


DEFAULT_AUTHORITY_COMPACT_CSV_PATH = Path(__file__).resolve().parents[2] / "authority_compact.csv"
SCHEMA_VERSION = "2"
CORPUS_MODES = ("all", "intersection", "rest")
_ARTICLES = {"a", "an", "the"}


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
