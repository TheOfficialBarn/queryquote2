"""Prologue:
Command-line entry points for building, searching, and evaluating QueryQuote indexes.
Last updated: 2026-04-26 - Added corpus-mode support for v2 builds so
intersection and rest indexes can be generated separately with ETA progress.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import DEFAULT_MAX_PASSAGE_TOKENS, DEFAULT_PASSAGE_OVERLAP, DEFAULT_TOP_K
from .db_index import SQLiteSearchEngine, build_sqlite_index
from .db_index_v2 import build_sqlite_index_v2
from .evaluation import evaluate_run, load_qrels, load_queries
from .indexing import IndexBundle, build_index, save_index
from .passages import collect_passages
from .search_engine import SearchEngine


def cmd_build(args: argparse.Namespace) -> None:
    if args.backend == "sqlite":
        db_path = build_sqlite_index(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            max_passage_tokens=args.max_passage_tokens,
            passage_overlap=args.passage_overlap,
            progress_every_files=args.progress_every_files,
        )
        print(f"Indexed corpus into SQLite DB: {db_path}")
        return

    passages = collect_passages(
        args.data_dir,
        max_tokens=args.max_passage_tokens,
        overlap=args.passage_overlap,
    )
    index = build_index(passages)
    bundle = IndexBundle(index=index, passages=passages)
    save_index(bundle, args.output_dir)
    print(
        f"Indexed {len(passages)} passages from {args.data_dir} -> {Path(args.output_dir) / 'index_bundle.pkl'}"
    )


def cmd_build_v2(args: argparse.Namespace) -> None:
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
    if args.backend == "sqlite":
        engine = SQLiteSearchEngine.from_index_dir(args.index_dir)
    else:
        engine = SearchEngine.from_index_dir(args.index_dir)

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
    if args.backend == "sqlite":
        engine = SQLiteSearchEngine.from_index_dir(args.index_dir)
    else:
        engine = SearchEngine.from_index_dir(args.index_dir)

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QueryQuote IR system")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Build passage index from transcripts")
    p_build.add_argument("--data-dir", required=True, help="Path to transcript .txt files")
    p_build.add_argument("--output-dir", required=True, help="Where to save index")
    p_build.add_argument(
        "--backend",
        choices=["sqlite", "pickle"],
        default="sqlite",
        help="Index storage backend (sqlite is streaming and reusable)",
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

    p_search = sub.add_parser("search", help="Search by quote text")
    p_search.add_argument("--index-dir", required=True)
    p_search.add_argument(
        "--backend",
        choices=["sqlite", "pickle"],
        default="sqlite",
        help="Search backend",
    )
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p_search.add_argument(
        "--authority-filter",
        action="store_true",
        help="Rerank matched movies by Metacritic vote-count authority",
    )
    p_search.set_defaults(func=cmd_search)

    p_eval = sub.add_parser("evaluate", help="Evaluate run against qrels")
    p_eval.add_argument("--index-dir", required=True)
    p_eval.add_argument(
        "--backend",
        choices=["sqlite", "pickle"],
        default="sqlite",
        help="Evaluation backend",
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
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
