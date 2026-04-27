"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Turns raw transcript files into *SEARCHABLE PASSAGE CHUNKS*

Last updated: 2026-04-27 - Added import comments explaining transcript path,
tokenization, and passage data-shape dependencies.
"""
from __future__ import annotations              # Defers annotations for path-like type hints.
from pathlib import Path                        # Recursively discovers transcript files and parses filenames.
from .analyzer_v1 import join_tokens, tokenize  # Splits raw transcript text into readable token windows.
from .types import Passage                      # Packages indexed passage metadata for callers.


def iter_transcript_files(data_dir: str | Path):
    """
    Finds every .txt transcript under a directory
    """
    data_path = Path(data_dir)
    yield from data_path.rglob("*.txt")     # So if the corpus has nested folders,
                                            # It still finds transcript files recursively


def movie_id_from_filename(file_name: str) -> str:
    """
    Turns a transcript filename into a movie ID
    """
    suffix = " - full transcript.txt"
    if file_name.endswith(suffix):
        return file_name[: -len(suffix)]
    return Path(file_name).stem


def split_text_into_passages(raw_text: str, *, max_tokens: int, overlap: int) -> list[str]:
    """
    Splits one transcript into passage-sized chunks
    """
    # Below we keep stopwords. We do this because this function is
    # Splitting text into readable passage windows to be displayed 
    # in frontend, not doing search-term filtering
    tokens = tokenize(raw_text, remove_stopwords=False)
    if not tokens: return []

    if max_tokens <= 0:
        raise ValueError("max_tokens must be > 0")
    if overlap < 0 or overlap >= max_tokens:
        raise ValueError("overlap must satisfy 0 <= overlap < max_tokens")

    passages: list[str] = []
    step = max_tokens - overlap
    for start in range(0, len(tokens), step):
        chunk = tokens[start : start + max_tokens]
        if not chunk:
            break
        passages.append(join_tokens(chunk))
        if start + max_tokens >= len(tokens):
            break
    return passages


def collect_passages(data_dir: str | Path, *, max_tokens: int, overlap: int) -> list[Passage]:
    """
    This is a convenience function that does the full passage collection
    1. Find transcript files
    2. Read each file
    3. Derive movie_id
    4. Split text into chunks
    5. Wrap each chunk in a *PASSAGE* dataclass
    """
    results: list[Passage] = []
    for path in iter_transcript_files(data_dir):
        text = path.read_text(encoding="utf-8", errors="ignore")
        movie_id = movie_id_from_filename(path.name)
        chunks = split_text_into_passages(text, max_tokens=max_tokens, overlap=overlap)
        for i, chunk in enumerate(chunks):
            passage_id = f"{movie_id}::p{i:04d}"
            results.append(
                Passage(
                    passage_id=passage_id,
                    movie_id=movie_id,
                    source_file=str(path),
                    raw_text=chunk,
                )
            )
    return results
