"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
CSV-backed authority scoring for opt-in movie ranking adjustments.

Last updated: 2026-04-27 - Added authority genre lookups so legacy search can
share the transcript browser's metadata filters.
"""

from __future__ import annotations  # Allows forward-looking type hints without runtime overhead.

import csv                          # Reads Metacritic authority rows from authority_compact.csv.
import math                         # Computes bounded log-scaled vote multipliers.
import re                           # Extracts years and strips title qualifiers for matching. (**REGEX**)
import unicodedata                  # Normalizes titles across accents and punctuation variants.
from dataclasses import dataclass   # Stores authority records and lookup indexes as explicit shapes.
from functools import lru_cache     # Caches the default authority index so searches do not reread CSV.
from pathlib import Path            # Resolves the repository-local authority CSV path.
from typing import Iterable         # Types caller-supplied authority row collections.


DEFAULT_AUTHORITY_CSV_PATH = Path(__file__).resolve().parents[2] / "authority_compact.csv"
MIN_AUTHORITY_MULTIPLIER = 0.75
MAX_AUTHORITY_MULTIPLIER = 1.25

# Pull years from either authority titles/release dates or transcript movie IDs.
_PAREN_YEAR_RE = re.compile(r"\((?P<year>(?:19|20)\d{2})\)")
_RELEASE_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
_TRAILING_MOVIE_ID_YEAR_RE = re.compile(r"\s+_(?P<year>(?:19|20)\d{2})_$")

# Remove edition labels before title matching so remasters/rereleases still align.
_QUALIFIER_PAREN_RE = re.compile(
    r"\((?:re[-\s]?release|restored|restoration|remaster(?:ed)?|"
    r"director'?s cut|extended|unrated|theatrical cut)\)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class AuthorityRecord:
    """One movie authority row after parsing vote count and multiplier."""

    title: str
    votes: int
    multiplier: float
    release_year: str | None = None
    genres: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AuthorityIndex:
    """Lookup tables used at query time to boost or dampen movie scores."""

    by_title: dict[str, AuthorityRecord]
    by_title_year: dict[tuple[str, str], AuthorityRecord]

    @classmethod
    def empty(cls) -> "AuthorityIndex":
        """Return a no-op index when the CSV is missing or has no valid rows."""
        return cls(by_title={}, by_title_year={})

    def record_for_movie_id(self, movie_id: str) -> AuthorityRecord | None:
        """Find the authority row for one transcript movie ID."""
        title, year = split_movie_id(movie_id)
        title_key = normalize_title(title)
        if not title_key:
            return None

        # Prefer exact title+year matches when the transcript ID carries a year.
        if year is not None:
            record = self.by_title_year.get((title_key, year))
            if record is not None:
                return record.multiplier

        # Fall back to title-only matches only when build_authority_index found
        # the title to be unambiguous across release years.
        return self.by_title.get(title_key)

    def multiplier_for_movie_id(self, movie_id: str) -> float | None:
        """Find the authority multiplier for one transcript movie ID."""
        record = self.record_for_movie_id(movie_id)
        return record.multiplier if record is not None else None

    def genres_for_movie_id(self, movie_id: str) -> list[str]:
        """Find Metacritic genres for one transcript movie ID."""
        record = self.record_for_movie_id(movie_id)
        return list(record.genres) if record is not None else []

    def all_genres(self) -> list[str]:
        """List every genre available in this authority index."""
        genres = {
            genre
            for record in [*self.by_title.values(), *self.by_title_year.values()]
            for genre in record.genres
        }
        return sorted(genres, key=str.casefold)


def normalize_title(value: str) -> str:
    """Normalize movie titles so CSV titles and transcript IDs can be compared."""
    ascii_value = (
        unicodedata.normalize("NFKD", value.replace("_", " "))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    without_noise = _PAREN_YEAR_RE.sub(" ", _QUALIFIER_PAREN_RE.sub(" ", ascii_value))
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", without_noise).lower()
    return re.sub(r"\s+", " ", words_only).strip()


def split_movie_id(movie_id: str) -> tuple[str, str | None]:
    """Split transcript IDs like 'Movie Name _1999_' into title and year."""
    clean_movie_id = movie_id.strip()
    match = _TRAILING_MOVIE_ID_YEAR_RE.search(clean_movie_id)
    if match is None:
        return clean_movie_id, None

    return clean_movie_id[: match.start()].strip(), match.group("year")


def build_authority_index(rows: Iterable[dict[str, str]]) -> AuthorityIndex:
    """Parse authority CSV rows into title and title-year lookup tables."""
    parsed_records: list[tuple[AuthorityRecord, set[str | None]]] = []
    max_votes = 0

    # First pass validates rows and records max_votes for normalized multipliers.
    for row in rows:
        title = (row.get("Title") or "").strip()
        votes = parse_vote_count(row.get("No of Persons Voted", ""))
        if not title or votes is None:
            continue

        max_votes = max(max_votes, votes)
        years = {
            parse_release_year(row.get("Release Date", "")),
            parse_title_year(title),
        }
        parsed_records.append(
            (
                AuthorityRecord(
                    title=title,
                    votes=votes,
                    multiplier=1.0,
                    release_year=parse_release_year(row.get("Release Date", "")),
                    genres=tuple(_split_genres(row.get("Genres"))),
                ),
                years,
            )
        )

    if not parsed_records or max_votes <= 0:
        return AuthorityIndex.empty()

    by_title_year: dict[tuple[str, str], AuthorityRecord] = {}
    records_by_title: dict[str, list[AuthorityRecord]] = {}

    # Second pass computes multipliers now that the global max vote count is known.
    for record, years in parsed_records:
        multiplier = authority_multiplier(record.votes, max_votes=max_votes)
        weighted_record = AuthorityRecord(
            title=record.title,
            votes=record.votes,
            multiplier=multiplier,
            release_year=record.release_year,
            genres=record.genres,
        )
        title_key = normalize_title(record.title)
        if not title_key:
            continue

        records_by_title.setdefault(title_key, []).append(weighted_record)
        for year in years:
            if year is None:
                continue
            _store_highest_vote_record(by_title_year, (title_key, year), weighted_record)

    by_title: dict[str, AuthorityRecord] = {}
    for title_key, records in records_by_title.items():
        years_for_title = {record.release_year for record in records if record.release_year}
        # Title-only fallback is safe only when a normalized title does not refer
        # to multiple release years in the authority CSV.
        if len(years_for_title) <= 1:
            by_title[title_key] = max(records, key=lambda record: record.votes)

    return AuthorityIndex(by_title=by_title, by_title_year=by_title_year)


def load_authority_index(csv_path: str | Path) -> AuthorityIndex:
    """Load an authority index from disk, using a small path-based cache."""
    return _load_authority_index_cached(str(Path(csv_path)))


def load_default_authority_index() -> AuthorityIndex:
    """Load the compact project authority CSV used by search by default."""
    return load_authority_index(DEFAULT_AUTHORITY_CSV_PATH)


def authority_multiplier(votes: int, *, max_votes: int) -> float:
    """Convert vote counts into a bounded ranking multiplier."""
    if votes <= 0 or max_votes <= 0:
        return MIN_AUTHORITY_MULTIPLIER

    # log1p keeps high-vote movies from dominating while preserving vote order.
    normalized_votes = math.log1p(votes) / math.log1p(max_votes)
    bounded_votes = min(1.0, max(0.0, normalized_votes))
    spread = MAX_AUTHORITY_MULTIPLIER - MIN_AUTHORITY_MULTIPLIER
    return MIN_AUTHORITY_MULTIPLIER + spread * bounded_votes


def parse_vote_count(value: str | None) -> int | None:
    """Parse CSV vote counts such as '12,345' into integers."""
    normalized = (value or "").strip().replace(",", "")
    if not normalized:
        return None
    return int(normalized) if normalized.isdigit() else None


def parse_release_year(value: str | None) -> str | None:
    """Extract the first release year from a CSV date string."""
    match = _RELEASE_YEAR_RE.search(value or "")
    return match.group(1) if match is not None else None


def parse_title_year(value: str | None) -> str | None:
    """Extract a parenthesized title year such as 'Movie (1999)'."""
    match = _PAREN_YEAR_RE.search(value or "")
    return match.group("year") if match is not None else None


@lru_cache(maxsize=8)
def _load_authority_index_cached(csv_path: str) -> AuthorityIndex:
    """Read and cache authority CSV files so engine startup can reuse indexes."""
    path = Path(csv_path)
    if not path.exists():
        return AuthorityIndex.empty()

    with path.open(newline="", encoding="utf-8-sig") as handle:
        return build_authority_index(csv.DictReader(handle))


def _store_highest_vote_record(
    records: dict[tuple[str, str], AuthorityRecord],
    key: tuple[str, str],
    record: AuthorityRecord,
) -> None:
    """Keep the highest-vote authority record for duplicate title-year keys."""
    current = records.get(key)
    if current is None or record.votes > current.votes:
        records[key] = record


def _split_genres(value: str | None) -> list[str]:
    """Split the compact CSV genre column without importing transcript helpers."""
    if not value:
        return []

    return [genre.strip() for genre in value.split(",") if genre.strip()]
