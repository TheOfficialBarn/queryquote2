"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Shared helpers for transcript browser lookup, limit handling, and source-file
resolution across SQLite index versions.

Last updated: 2026-04-27 - Added multi-select genre and decade helpers for
transcript browser filters backed by the authority metadata in the v2 index.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSCRIPT_LIMIT = 40
MAX_TRANSCRIPT_LIMIT = 100


def bounded_transcript_limit(
    value: object,
    *,
    default: int = DEFAULT_TRANSCRIPT_LIMIT,
    maximum: int = MAX_TRANSCRIPT_LIMIT,
) -> int:
    """Convert user-provided limits into a small, predictable API page size."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    return max(1, min(parsed, maximum))


def escape_sql_like(value: str) -> str:
    """Escape wildcard characters before using a user query with SQLite LIKE."""
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def normalized_transcript_decade(value: object) -> int | None:
    """Convert decade filter values like 1980 into a safe start year."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    if parsed < 1900 or parsed > 2030:
        return None

    return parsed - (parsed % 10)


def normalized_transcript_decades(values: list[object]) -> list[int]:
    """Normalize repeated decade filter values while preserving selection order."""
    decades: list[int] = []
    seen: set[int] = set()
    for value in values:
        decade = normalized_transcript_decade(value)
        if decade is not None and decade not in seen:
            decades.append(decade)
            seen.add(decade)
    return decades


def normalized_transcript_genres(values: list[str]) -> list[str]:
    """Normalize repeated genre filter values while preserving selection order."""
    genres: list[str] = []
    seen: set[str] = set()
    for value in values:
        genre = value.strip()
        key = genre.casefold()
        if genre and key not in seen:
            genres.append(genre)
            seen.add(key)
    return genres


def split_authority_genres(value: str | None) -> list[str]:
    """Split Metacritic genre strings stored in compact CSV/index rows."""
    if not value:
        return []

    return [genre.strip() for genre in value.split(",") if genre.strip()]


def resolve_transcript_source(source_file: str) -> Path:
    """Resolve index source paths whether they were stored from repo or backend cwd."""
    source_path = Path(source_file)
    candidates = (
        source_path,
        PROJECT_ROOT / source_path,
        BACKEND_ROOT / source_path,
        PROJECT_ROOT / "backend" / source_path,
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    return candidates[0].resolve()


def read_transcript_source(source_file: str) -> tuple[str, str]:
    """Read transcript text and return it with the resolved path used."""
    resolved_source = resolve_transcript_source(source_file)
    return (
        resolved_source.read_text(encoding="utf-8", errors="replace"),
        str(resolved_source),
    )
