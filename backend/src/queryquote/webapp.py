"""Prologue:
API-only Flask application for QueryQuote search endpoints.
Last updated: 2026-04-25 - Added an opt-in authority filter request flag that
lets clients rerank results with Metacritic vote-count weighting.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from flask import Flask, jsonify, request

from .config import DEFAULT_TOP_K
from .db_index import SQLiteSearchEngine
from .search_engine import SearchEngine


def create_app(index_dir: str, backend: str = "sqlite") -> Flask:
    """Create and configure the Flask application.

    Args:
        index_dir: Path to the index directory
        backend: Index backend ("sqlite" or "pickle")

    Returns:
        Configured Flask app
    """
    app = Flask(__name__)

    # Load search engine
    try:
        if backend == "sqlite":
            search_engine = SQLiteSearchEngine.from_index_dir(index_dir)
        else:
            search_engine = SearchEngine.from_index_dir(index_dir)
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
                "top_k": 10,  (optional, default 10)
                "authority_filter": false  (optional, default false)
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
                "authority_filter": false,
                "count": 5
            }
        """
        try:
            data = request.get_json() or {}
            query = data.get("query", "").strip()
            top_k = data.get("top_k", DEFAULT_TOP_K)
            authority_filter = data.get("authority_filter") is True

            if not query:
                return jsonify(
                    {"error": "Query is required", "results": [], "count": 0}
                ), 400

            results = search_engine.search(
                query,
                top_k=top_k,
                authority_filter=authority_filter,
            )

            return jsonify(
                {
                    "query": query,
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
        return jsonify({"status": "ok"})

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
        choices=["sqlite", "pickle"],
        help="Index backend (default: sqlite)",
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
    app = create_app(str(index_dir), backend=args.backend)

    print(f"Starting server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
