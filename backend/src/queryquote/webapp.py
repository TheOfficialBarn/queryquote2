"""Prologue:
API-only Flask application for QueryQuote search endpoints.
Last updated: 2026-04-27 - Removed deprecated pickle backend support so the API
serves SQLite v1 and SQLite v2 indexes only.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from flask import Flask, jsonify, request

from .config import DEFAULT_TOP_K
from .db_index import SQLiteSearchEngine
from .db_index_v2 import SQLiteSearchEngineV2


def create_app(
    index_dir: str,
    backend: str = "sqlite",
    *,
    v2_index_dir: str | None = None,
    default_index_version: str = "v1",
) -> Flask:
    """Create and configure the Flask application.

    Args:
        index_dir: Path to the index directory
        backend: Index backend ("sqlite", "sqlite-v1", or "sqlite-v2")
        v2_index_dir: Optional v2 index directory for side-by-side API comparisons.
        default_index_version: Index version used when the request omits one.

    Returns:
        Configured Flask app
    """
    app = Flask(__name__)

    # Load engines once at startup so request handling only selects a version.
    try:
        search_engines: dict[str, object] = {}
        if backend in {"sqlite", "sqlite-v1"}:
            search_engines["v1"] = SQLiteSearchEngine.from_index_dir(index_dir)
        elif backend == "sqlite-v2":
            search_engines["v2"] = SQLiteSearchEngineV2.from_index_dir(index_dir)
            default_index_version = "v2"
        else:
            raise ValueError(f"Unsupported backend: {backend}")

        if v2_index_dir is not None and "v2" not in search_engines:
            search_engines["v2"] = SQLiteSearchEngineV2.from_index_dir(v2_index_dir)

        if default_index_version not in search_engines:
            default_index_version = "v1" if "v1" in search_engines else "v2"
    except Exception as e:
        app.logger.error(f"Failed to load index from {index_dir}: {e}")
        raise

    @app.route("/", methods=["GET"])
    def root() -> str:
        """Describe available API endpoints."""
        return jsonify(
            {
                "service": "queryquote-api",
                "status": "ok",
                "default_index_version": default_index_version,
                "available_index_versions": sorted(search_engines),
                "endpoints": {
                    "health": "/api/health",
                    "search": "/api/search",
                },
            }
        )

    @app.route("/api/search", methods=["POST"])
    def search() -> str:
        """Search for quotes.

        Request JSON:
            {
                "query": "search query",
                "top_k": 50,  (optional, default 50)
                "authority_filter": false,  (optional, default false)
                "index_version": "v1"  (optional, "v1" or "v2")
            }

        Returns:
            JSON with results:
            {
                "results": [
                    {
                        "passage_id": "movie_id::p1",
                        "movie_id": "movie_id",
                        "score": 0.95,
                        "snippet": "quote text...",
                        "source_file": "filename.txt"
                    },
                    ...
                ],
                "query": "search query",
                "index_version": "v1",
                "authority_filter": false,
                "count": 5
            }
        """
        try:
            data = request.get_json() or {}
            query = data.get("query", "").strip()
            top_k = data.get("top_k", DEFAULT_TOP_K)
            authority_filter = data.get("authority_filter") is True
            index_version = data.get("index_version", default_index_version)

            if not query:
                return jsonify(
                    {"error": "Query is required", "results": [], "count": 0}
                ), 400

            if index_version not in search_engines:
                return jsonify(
                    {
                        "error": f"Index version is not available: {index_version}",
                        "available_index_versions": sorted(search_engines),
                        "results": [],
                        "count": 0,
                    }
                ), 400

            search_engine = search_engines[index_version]
            results = search_engine.search(
                query,
                top_k=top_k,
                authority_filter=authority_filter,
            )

            return jsonify(
                {
                    "query": query,
                    "index_version": index_version,
                    "authority_filter": authority_filter,
                    "results": [
                        {
                            "passage_id": r.passage_id,
                            "movie_id": r.movie_id,
                            "score": float(r.score),
                            "snippet": r.snippet,
                            "source_file": r.source_file,
                        }
                        for r in results
                    ],
                    "count": len(results),
                }
            )

        except Exception as e:
            app.logger.error(f"Search error: {e}", exc_info=True)
            return jsonify({"error": str(e), "results": [], "count": 0}), 500

    @app.route("/api/health", methods=["GET"])
    def health() -> str:
        """Health check endpoint."""
        return jsonify(
            {
                "status": "ok",
                "default_index_version": default_index_version,
                "available_index_versions": sorted(search_engines),
            }
        )

    return app


def main() -> None:
    """Run the Flask API app from command line."""
    parser = argparse.ArgumentParser(description="QueryQuote API Server")
    parser.add_argument(
        "--index-dir",
        required=True,
        help="Path to the search index directory",
    )
    parser.add_argument(
        "--backend",
        default="sqlite",
        choices=["sqlite", "sqlite-v1", "sqlite-v2"],
        help="Index backend (default: sqlite)",
    )
    parser.add_argument(
        "--v2-index-dir",
        default=None,
        help="Optional v2 SQLite index directory for side-by-side API comparisons",
    )
    parser.add_argument(
        "--default-index-version",
        default="v1",
        choices=["v1", "v2"],
        help="Default index version for requests that omit index_version",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Server port (default: 5000)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode",
    )

    args = parser.parse_args()

    index_dir = Path(args.index_dir)
    if not index_dir.exists():
        print(f"Error: Index directory not found: {index_dir}")
        return

    print(f"Loading {args.backend} index from {index_dir}...")
    if args.v2_index_dir:
        print(f"Loading v2 index from {args.v2_index_dir}...")
    app = create_app(
        str(index_dir),
        backend=args.backend,
        v2_index_dir=args.v2_index_dir,
        default_index_version=args.default_index_version,
    )

    print(f"Starting server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
