"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Command-line entry points for building, searching, and evaluating QueryQuote indexes.

Last updated: 2026-04-27 - Added short review comments explaining the CLI
command handlers, backend selection, and parser setup.
"""

from __future__ import annotations

import argparse
import json

from .config import DEFAULT_MAX_PASSAGE_TOKENS, DEFAULT_PASSAGE_OVERLAP, DEFAULT_TOP_K
from .db_index import SQLiteSearchEngine, build_sqlite_index
from .db_index_v2 import SQLiteSearchEngineV2, build_sqlite_index_v2
from .evaluation import evaluate_run, load_qrels, load_queries


def cmd_build(args: argparse.Namespace) -> None:
    # Builds the v1 SQLite postings database used by Legacy Search.
    # Full-corpus builds can take many hours; keep the machine awake while running.
    db_path = build_sqlite_index(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        max_passage_tokens=args.max_passage_tokens,
        passage_overlap=args.passage_overlap,
        progress_every_files=args.progress_every_files,
    )
    print(f"Indexed corpus into SQLite DB: {db_path}")


def cmd_build_v2(args: argparse.Namespace) -> None:
    # Builds a v2 SQLite postings database for all, intersection, or rest corpus modes.
    # Split-corpus builds are official, and full/rest builds can take many hours.
    db_path = build_sqlite_index_v2(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        authority_csv_path=args.authority_csv,
        max_passage_tokens=args.max_passage_tokens,
        passage_overlap=args.passage_overlap,
        progress_every_files=args.progress_every_files,
        batch_size=args.batch_size,
        corpus_mode=args.corpus_mode,
    )
    print(f"Indexed corpus into SQLite v2 DB: {db_path}")


def cmd_search(args: argparse.Namespace) -> None:
    # Load the requested SQLite engine, run one query, and print ranked passages.
    engine = _load_search_engine(args)

    results = engine.search(
        args.query,
        top_k=args.top_k,
        authority_filter=args.authority_filter,
    )
    if not results:
        print("No results found.")
        return

    for i, r in enumerate(results, start=1):
        print(f"[{i}] score={r.score:.4f} movie={r.movie_id} passage={r.passage_id}")
        print(f"    file: {r.source_file}")
        print(f"    text: {r.snippet}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    # Replay a query set through one engine, then score the run against qrels.
    engine = _load_search_engine(args)

    queries = load_queries(args.queries)
    qrels = load_qrels(args.qrels)

    run: dict[str, list[str]] = {}
    for row in queries:
        qid = row["qid"]
        q = row["query"]
        results = engine.search(q, top_k=args.top_k, authority_filter=args.authority_filter)
        run[qid] = [r.passage_id for r in results]

    metrics = evaluate_run(run, qrels, k=args.top_k)
    print(json.dumps(metrics, indent=2))


def _load_search_engine(args: argparse.Namespace):
    # Centralize v1/v2 selection so search and evaluation use the same routing.
    backend = args.backend
    index_version = getattr(args, "index_version", "v1")

    # Explicit sqlite-v2, or generic sqlite with --index-version v2, loads v2.
    if backend == "sqlite-v2" or (backend in {"sqlite", "sqlite-v1"} and index_version == "v2"):
        v2_index_dir = getattr(args, "v2_index_dir", None) or args.index_dir
        return SQLiteSearchEngineV2.from_index_dir(v2_index_dir)

    # sqlite and sqlite-v1 both mean the original SQLite v1 index.
    if backend in {"sqlite", "sqlite-v1"}:
        return SQLiteSearchEngine.from_index_dir(args.index_dir)
    raise ValueError(f"Unsupported backend: {backend}")


def build_parser() -> argparse.ArgumentParser:
    # argparse owns the command surface for the installed `queryquote` CLI.
    parser = argparse.ArgumentParser(description="QueryQuote IR system")
    sub = parser.add_subparsers(dest="command", required=True)

    # v1 index builder: writes the original SQLite postings index.
    p_build = sub.add_parser("build", help="Build passage index from transcripts")
    p_build.add_argument("--data-dir", required=True, help="Path to transcript .txt files")
    p_build.add_argument("--output-dir", required=True, help="Where to save index")
    p_build.add_argument(
        "--backend",
        choices=["sqlite", "sqlite-v1"],
        default="sqlite",
        help="Index storage backend",
    )
    p_build.add_argument(
        "--max-passage-tokens",
        type=int,
        default=DEFAULT_MAX_PASSAGE_TOKENS,
        help="Sliding window passage size",
    )
    p_build.add_argument(
        "--passage-overlap",
        type=int,
        default=DEFAULT_PASSAGE_OVERLAP,
        help="Token overlap between consecutive passages",
    )
    p_build.add_argument(
        "--progress-every-files",
        type=int,
        default=500,
        help="Progress print interval for sqlite backend",
    )
    p_build.set_defaults(func=cmd_build)

    # v2 index builder: writes the newer SQLite schema and supports corpus splits.
    p_build_v2 = sub.add_parser(
        "build-v2",
        help="Build separate v2 SQLite postings from transcripts",
    )
    p_build_v2.add_argument("--data-dir", required=True, help="Path to transcript .txt files")
    p_build_v2.add_argument(
        "--output-dir",
        default="data2",
        help="Where to save the v2 SQLite index",
    )
    p_build_v2.add_argument(
        "--authority-csv",
        default=None,
        help="Compact authority CSV path; defaults to backend/authority_compact.csv",
    )
    p_build_v2.add_argument(
        "--max-passage-tokens",
        type=int,
        default=DEFAULT_MAX_PASSAGE_TOKENS,
        help="Sliding window passage size",
    )
    p_build_v2.add_argument(
        "--passage-overlap",
        type=int,
        default=DEFAULT_PASSAGE_OVERLAP,
        help="Token overlap between consecutive passages",
    )
    p_build_v2.add_argument(
        "--progress-every-files",
        type=int,
        default=1000,
        help="Progress/ETA print interval",
    )
    p_build_v2.add_argument(
        "--batch-size",
        type=int,
        default=50000,
        help="SQLite insert batch size",
    )
    p_build_v2.add_argument(
        "--corpus-mode",
        choices=["all", "intersection", "rest"],
        default="all",
        help="Which transcript subset to index",
    )
    p_build_v2.set_defaults(func=cmd_build_v2)

    # Search command: runs one quote query and prints the top ranked passages.
    p_search = sub.add_parser("search", help="Search by quote text")
    p_search.add_argument("--index-dir", required=True)
    p_search.add_argument(
        "--backend",
        choices=["sqlite", "sqlite-v1", "sqlite-v2"],
        default="sqlite",
        help="Search backend",
    )
    p_search.add_argument(
        "--index-version",
        choices=["v1", "v2"],
        default="v1",
        help="SQLite index version to query when backend is sqlite",
    )
    p_search.add_argument(
        "--v2-index-dir",
        default=None,
        help="Optional v2 SQLite index directory when querying v2 side-by-side",
    )
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p_search.add_argument(
        "--authority-filter",
        action="store_true",
        help="Rerank matched movies by Metacritic vote-count authority",
    )
    p_search.set_defaults(func=cmd_search)

    # Evaluation command: computes IR metrics from query and qrel JSONL files.
    p_eval = sub.add_parser("evaluate", help="Evaluate run against qrels")
    p_eval.add_argument("--index-dir", required=True)
    p_eval.add_argument(
        "--backend",
        choices=["sqlite", "sqlite-v1", "sqlite-v2"],
        default="sqlite",
        help="Evaluation backend",
    )
    p_eval.add_argument(
        "--index-version",
        choices=["v1", "v2"],
        default="v1",
        help="SQLite index version to evaluate when backend is sqlite",
    )
    p_eval.add_argument(
        "--v2-index-dir",
        default=None,
        help="Optional v2 SQLite index directory when evaluating v2 side-by-side",
    )
    p_eval.add_argument("--queries", required=True, help="JSONL with qid/query")
    p_eval.add_argument("--qrels", required=True, help="JSONL with qid/doc_id/relevance")
    p_eval.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p_eval.add_argument(
        "--authority-filter",
        action="store_true",
        help="Rerank matched movies by Metacritic vote-count authority",
    )
    p_eval.set_defaults(func=cmd_evaluate)

    return parser


def main() -> None:
    # Dispatch to the handler attached by the selected subcommand.
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
