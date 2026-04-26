"""Prologue:
CSV-backed authority scoring for opt-in movie ranking adjustments.
Last updated: 2026-04-25 - Added Metacritic vote-count loading and bounded
ranking multipliers so high-vote movies can be boosted and sparse-vote movies
can be penalized only when the authority filter is enabled.
"""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


DEFAULT_AUTHORITY_CSV_PATH = Path(__file__).resolve().parents[2] / "authority.csv"
MIN_AUTHORITY_MULTIPLIER = 0.75
MAX_AUTHORITY_MULTIPLIER = 1.25

_PAREN_YEAR_RE = re.compile(r"\((?P<year>(?:19|20)\d{2})\)")
_RELEASE_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
_TRAILING_MOVIE_ID_YEAR_RE = re.compile(r"\s+_(?P<year>(?:19|20)\d{2})_$")
_QUALIFIER_PAREN_RE = re.compile(
    r"\((?:re[-\s]?release|restored|restoration|remaster(?:ed)?|"
    r"director'?s cut|extended|unrated|theatrical cut)\)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class AuthorityRecord:
    title: str
    votes: int
    multiplier: float
    release_year: str | None = None


@dataclass(frozen=True, slots=True)
class AuthorityIndex:
    by_title: dict[str, AuthorityRecord]
    by_title_year: dict[tuple[str, str], AuthorityRecord]

    @classmethod
    def empty(cls) -> "AuthorityIndex":
        return cls(by_title={}, by_title_year={})

    def multiplier_for_movie_id(self, movie_id: str) -> float | None:
        title, year = split_movie_id(movie_id)
        title_key = normalize_title(title)
        if not title_key:
            return None

        if year is not None:
            record = self.by_title_year.get((title_key, year))
            if record is not None:
                return record.multiplier

        record = self.by_title.get(title_key)
        return record.multiplier if record is not None else None


def normalize_title(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value.replace("_", " "))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    without_noise = _PAREN_YEAR_RE.sub(" ", _QUALIFIER_PAREN_RE.sub(" ", ascii_value))
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", without_noise).lower()
    return re.sub(r"\s+", " ", words_only).strip()


def split_movie_id(movie_id: str) -> tuple[str, str | None]:
    clean_movie_id = movie_id.strip()
    match = _TRAILING_MOVIE_ID_YEAR_RE.search(clean_movie_id)
    if match is None:
        return clean_movie_id, None

    return clean_movie_id[: match.start()].strip(), match.group("year")


def build_authority_index(rows: Iterable[dict[str, str]]) -> AuthorityIndex:
    parsed_records: list[tuple[AuthorityRecord, set[str | None]]] = []
    max_votes = 0

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
                ),
                years,
            )
        )

    if not parsed_records or max_votes <= 0:
        return AuthorityIndex.empty()

    by_title_year: dict[tuple[str, str], AuthorityRecord] = {}
    records_by_title: dict[str, list[AuthorityRecord]] = {}

    for record, years in parsed_records:
        multiplier = authority_multiplier(record.votes, max_votes=max_votes)
        weighted_record = AuthorityRecord(
            title=record.title,
            votes=record.votes,
            multiplier=multiplier,
            release_year=record.release_year,
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
        if len(years_for_title) <= 1:
            by_title[title_key] = max(records, key=lambda record: record.votes)

    return AuthorityIndex(by_title=by_title, by_title_year=by_title_year)


def load_authority_index(csv_path: str | Path) -> AuthorityIndex:
    return _load_authority_index_cached(str(Path(csv_path)))


def load_default_authority_index() -> AuthorityIndex:
    return load_authority_index(DEFAULT_AUTHORITY_CSV_PATH)


def authority_multiplier(votes: int, *, max_votes: int) -> float:
    if votes <= 0 or max_votes <= 0:
        return MIN_AUTHORITY_MULTIPLIER

    normalized_votes = math.log1p(votes) / math.log1p(max_votes)
    bounded_votes = min(1.0, max(0.0, normalized_votes))
    spread = MAX_AUTHORITY_MULTIPLIER - MIN_AUTHORITY_MULTIPLIER
    return MIN_AUTHORITY_MULTIPLIER + spread * bounded_votes


def parse_vote_count(value: str | None) -> int | None:
    normalized = (value or "").strip().replace(",", "")
    if not normalized:
        return None
    return int(normalized) if normalized.isdigit() else None


def parse_release_year(value: str | None) -> str | None:
    match = _RELEASE_YEAR_RE.search(value or "")
    return match.group(1) if match is not None else None


def parse_title_year(value: str | None) -> str | None:
    match = _PAREN_YEAR_RE.search(value or "")
    return match.group("year") if match is not None else None


@lru_cache(maxsize=8)
def _load_authority_index_cached(csv_path: str) -> AuthorityIndex:
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
    current = records.get(key)
    if current is None or record.votes > current.votes:
        records[key] = record
