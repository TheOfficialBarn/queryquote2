"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:

"""
from __future__ import annotations

from pathlib import Path

from .preprocessing import join_tokens, tokenize
from .types import Passage


def iter_transcript_files(data_dir: str | Path):
    data_path = Path(data_dir)
    yield from data_path.rglob("*.txt")


def movie_id_from_filename(file_name: str) -> str:
    suffix = " - full transcript.txt"
    if file_name.endswith(suffix):
        return file_name[: -len(suffix)]
    return Path(file_name).stem


def split_text_into_passages(raw_text: str, *, max_tokens: int, overlap: int) -> list[str]:
    tokens = tokenize(raw_text, remove_stopwords=False)
    if not tokens:
        return []

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
