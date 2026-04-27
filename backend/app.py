#!/usr/bin/env python3
"""Prologue:
Quick launcher for the QueryQuote API server.
Last updated: 2026-04-27 - Added import comments explaining the launcher-only
dependencies used to start the local Flask API.
"""

from __future__ import annotations          # Keep type hints lazy so this launcher stays compatible across supported Python versions.
import sys                                  # Lets the launcher prepend backend/src before importing the package.
from pathlib import Path                    # Builds portable paths to the local src package and index directories.
from queryquote.webapp import create_app    # Constructs the Flask API with the requested search indexes.
import argparse                             # Parses local server flags without loading CLI-only code at module import time.

# Add src to path so we can import queryquote
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main() -> None:
    """Run the API server."""

    parser = argparse.ArgumentParser(
        description="Launch QueryQuote API Server",
        epilog="Example: python backend/app.py --index-dir backend/data/index",
    )
    parser.add_argument(
        "--index-dir",
        help="Path to the index directory (required)",
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
        "--debug",
        action="store_true",
        help="Run in debug mode with auto-reload",
    )

    args = parser.parse_args()

    # Check for index directory
    if not args.index_dir:
        print("Error: --index-dir is required")
        print(
            "Usage: python backend/app.py --index-dir <path/to/index> [--host HOST] [--port PORT] [--debug]"
        )
        sys.exit(1)

    index_dir = Path(args.index_dir)
    if not index_dir.exists():
        print(f"Error: Index directory not found: {index_dir}")
        sys.exit(1)

    print(f"Loading {args.backend} index from {index_dir}...")
    if args.v2_index_dir:
        print(f"Loading v2 index from {args.v2_index_dir}...")
    app = create_app(
        str(index_dir),
        backend=args.backend,
        v2_index_dir=args.v2_index_dir,
        default_index_version=args.default_index_version,
    )

    url = f"http://{args.host}:{args.port}"
    print("\nQueryQuote API Server")
    print(f"Base URL: {url}")
    print("Health endpoint: /api/health")
    print("Search endpoint: POST /api/search")
    print("Press Ctrl+C to stop\n")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
