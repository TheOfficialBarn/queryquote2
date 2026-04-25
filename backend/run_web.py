#!/usr/bin/env python3
"""Prologue:
Quick launcher for the QueryQuote API server.
Last updated: Messaging now reflects API-only backend usage (no built-in UI).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path so we can import queryquote
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from queryquote.webapp import create_app


def main() -> None:
    """Run the API server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch QueryQuote API Server",
        epilog="Example: python run_web.py --index-dir data/index",
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
        choices=["sqlite", "pickle"],
        help="Index backend (default: sqlite)",
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
            "Usage: python run_web.py --index-dir <path/to/index> [--host HOST] [--port PORT] [--debug]"
        )
        sys.exit(1)

    index_dir = Path(args.index_dir)
    if not index_dir.exists():
        print(f"Error: Index directory not found: {index_dir}")
        sys.exit(1)

    print(f"Loading {args.backend} index from {index_dir}...")
    app = create_app(str(index_dir), backend=args.backend)

    url = f"http://{args.host}:{args.port}"
    print("\nQueryQuote API Server")
    print(f"Base URL: {url}")
    print("Health endpoint: /api/health")
    print("Search endpoint: POST /api/search")
    print("Press Ctrl+C to stop\n")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
