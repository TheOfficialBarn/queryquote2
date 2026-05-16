"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Parallel comparison runner for v1, v1 authority boost, v2, and v2 authority boost
against a fixed set of quote test cases.

Last updated: 2026-04-27 - Added a multiprocessing benchmark script that records
P@10 placement or FALSE plus elapsed search time for each engine variant.
"""

from __future__ import annotations

import argparse
import csv
import os
import queue
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import multiprocessing
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
DEFAULT_CASES_PATH = REPO_ROOT / "test" / "test-cases" / "test-cases-1.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "test" / "engine-comparisons"
DEFAULT_V1_INDEX_DIR = REPO_ROOT / "backend" / "data" / "index"
DEFAULT_V2_INDEX_DIR = REPO_ROOT / "backend" / "data2_intersection"
VARIANTS = (
    ("v1", "v1", False),
    ("v1_authority", "v1", True),
    ("v2", "v2", False),
    ("v2_authority", "v2", True),
)
_PROGRESS_QUEUE: Any | None = None


@dataclass(frozen=True, slots=True)
class QuoteCase:
    case_id: int
    quote: str
    expected_movie: str


def _ensure_backend_import_path() -> None:
    # Workers start fresh processes, so each process must add the local package path.
    backend_src = str(BACKEND_SRC)
    if backend_src not in sys.path:
        sys.path.insert(0, backend_src)


def _load_cases(path: Path, limit: int) -> list[QuoteCase]:
    cases: list[QuoteCase] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            quote = (row.get("Quote") or row.get("quote") or "").strip()
            movie = (row.get("Movie") or row.get("movie") or "").strip()
            if not quote or not movie:
                continue
            cases.append(QuoteCase(case_id=index, quote=quote, expected_movie=movie))
            if len(cases) >= limit:
                break
    return cases


def _load_engine(index_version: str, v1_index_dir: str, v2_index_dir: str) -> Any:
    _ensure_backend_import_path()
    if index_version == "v1":
        from queryquote.db_index import SQLiteSearchEngine

        return SQLiteSearchEngine.from_index_dir(v1_index_dir)
    if index_version == "v2":
        from queryquote.db_index_v2 import SQLiteSearchEngineV2

        return SQLiteSearchEngineV2.from_index_dir(v2_index_dir)
    raise ValueError(f"Unsupported index version: {index_version}")


def _init_worker(progress_queue: Any) -> None:
    # ProcessPoolExecutor initializers let forked workers share one parent-owned queue.
    global _PROGRESS_QUEUE
    _PROGRESS_QUEUE = progress_queue


def _normalized_title(value: str) -> str:
    _ensure_backend_import_path()
    from queryquote.authority import normalize_title, split_movie_id

    title, _ = split_movie_id(value)
    return normalize_title(title)


def _placement_at_10(results: list[Any], expected_movie: str) -> int | bool:
    expected = _normalized_title(expected_movie)
    if not expected:
        return False

    for placement, result in enumerate(results[:10], start=1):
        actual = _normalized_title(result.movie_id)
        # Allow broad case labels like "Star Wars" to match specific indexed titles.
        if actual == expected or expected in actual or actual in expected:
            return placement
    return False


def _run_variant(
    *,
    variant_name: str,
    index_version: str,
    authority_boost: bool,
    cases: list[QuoteCase],
    v1_index_dir: str,
    v2_index_dir: str,
) -> list[dict[str, Any]]:
    engine = _load_engine(index_version, v1_index_dir, v2_index_dir)
    rows: list[dict[str, Any]] = []

    for case in cases:
        started_at = time.perf_counter()
        results = engine.search(case.quote, top_k=10, authority_filter=authority_boost)
        elapsed_seconds = time.perf_counter() - started_at
        placement = _placement_at_10(results, case.expected_movie)
        rows.append(
            {
                "case_id": case.case_id,
                "quote": case.quote,
                "expected_movie": case.expected_movie,
                "variant": variant_name,
                "index_version": index_version,
                "authority_boost": authority_boost,
                "p_at_10_placement": placement if placement is not False else "FALSE",
                "time_seconds": f"{elapsed_seconds:.6f}",
                "top_movie_id": results[0].movie_id if results else "",
                "top_passage_id": results[0].passage_id if results else "",
                "result_count": len(results),
            }
        )
        if _PROGRESS_QUEUE is not None:
            _PROGRESS_QUEUE.put(
                {
                    "case_id": case.case_id,
                    "variant": variant_name,
                    "elapsed_seconds": elapsed_seconds,
                    "placement": placement if placement is not False else "FALSE",
                }
            )

    return rows


def _write_csv(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_p10_times.csv"
    fieldnames = [
        "case_id",
        "quote",
        "expected_movie",
        "variant",
        "index_version",
        "authority_boost",
        "p_at_10_placement",
        "time_seconds",
        "top_movie_id",
        "top_passage_id",
        "result_count",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (row["case_id"], row["variant"])))
    return output_path


def _print_case_progress(
    *,
    progress_queue: Any,
    total_cases: int,
    total_variant_results: int,
    futures: list[Any],
) -> None:
    finished_by_case: dict[int, int] = {}
    received = 0
    while received < total_variant_results:
        try:
            message = progress_queue.get(timeout=0.5)
        except queue.Empty:
            for future in futures:
                if future.done() and future.exception() is not None:
                    raise future.exception()
            if all(future.done() for future in futures):
                raise RuntimeError(
                    f"Workers finished after {received}/{total_variant_results} progress events"
                )
            continue

        received += 1
        case_id = int(message["case_id"])
        finished_by_case[case_id] = finished_by_case.get(case_id, 0) + 1
        print(
            "[variant finished] "
            f"case={case_id}/{total_cases} "
            f"variant={message['variant']} "
            f"p_at_10={message['placement']} "
            f"time={message['elapsed_seconds']:.3f}s",
            flush=True,
        )

        if finished_by_case[case_id] == len(VARIANTS):
            print(f"[test case finished] case={case_id}/{total_cases}", flush=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run QueryQuote v1/v2 P@10 placement and timing comparisons."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--v1-index-dir", type=Path, default=DEFAULT_V1_INDEX_DIR)
    parser.add_argument("--v2-index-dir", type=Path, default=DEFAULT_V2_INDEX_DIR)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--workers",
        type=int,
        default=min(len(VARIANTS), os.cpu_count() or len(VARIANTS)),
        help="Process count for engine variants.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit must be greater than 0")
    if args.workers <= 0:
        raise SystemExit("--workers must be greater than 0")

    cases = _load_cases(args.cases, args.limit)
    if not cases:
        raise SystemExit(f"No test cases found in {args.cases}")
    if len(cases) < args.limit:
        print(
            f"[case file short] requested={args.limit} available={len(cases)} path={args.cases}",
            flush=True,
        )

    multiprocessing_context = multiprocessing.get_context("fork")
    progress_queue = multiprocessing_context.Queue()
    with ProcessPoolExecutor(
        max_workers=args.workers,
        mp_context=multiprocessing_context,
        initializer=_init_worker,
        initargs=(progress_queue,),
    ) as executor:
        futures = [
            executor.submit(
                _run_variant,
                variant_name=variant_name,
                index_version=index_version,
                authority_boost=authority_boost,
                cases=cases,
                v1_index_dir=str(args.v1_index_dir),
                v2_index_dir=str(args.v2_index_dir),
            )
            for variant_name, index_version, authority_boost in VARIANTS
        ]

        _print_case_progress(
            progress_queue=progress_queue,
            total_cases=len(cases),
            total_variant_results=len(cases) * len(VARIANTS),
            futures=futures,
        )

        rows: list[dict[str, Any]] = []
        for future in as_completed(futures):
            rows.extend(future.result())

    output_path = _write_csv(rows, args.output_dir)
    print(f"[complete] wrote {len(rows)} rows to {output_path}", flush=True)


if __name__ == "__main__":
    main()
