#!/usr/bin/env python3
"""
Diagnostic script to test if QueryQuote is properly configured and working.
Helps identify issues with the index, search engine, or API.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def check_index(index_dir: str) -> bool:
    """Check if index exists and is valid."""
    print(f"\n🔍 Checking index at: {index_dir}")
    index_path = Path(index_dir)

    if not index_path.exists():
        print(f"  ❌ Index directory not found: {index_dir}")
        return False

    print(f"  ✓ Index directory exists")

    db_path = index_path / "index.db"
    if not db_path.exists():
        print(f"  ❌ Database file not found: {db_path}")
        return False

    print(f"  ✓ Database file found")

    # Check database size
    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Database size: {db_size_mb:.1f} MB")

    return True


def check_search_engine(index_dir: str, backend: str = "sqlite") -> bool:
    """Test if search engine can be loaded."""
    print(f"\n🔧 Testing search engine ({backend} backend):")

    try:
        if backend == "sqlite":
            from queryquote.db_index import SQLiteSearchEngine

            engine = SQLiteSearchEngine.from_index_dir(index_dir)
        else:
            from queryquote.search_engine import SearchEngine

            engine = SearchEngine.from_index_dir(index_dir)

        print(f"  ✓ Search engine loaded successfully")
        print(f"  ✓ Index contains {getattr(engine, 'num_docs', 'N/A')} documents")
        return True

    except Exception as e:
        print(f"  ❌ Error loading search engine: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_search(index_dir: str, backend: str = "sqlite") -> bool:
    """Test a simple search query."""
    print(f"\n🔎 Testing search functionality:")

    try:
        if backend == "sqlite":
            from queryquote.db_index import SQLiteSearchEngine

            engine = SQLiteSearchEngine.from_index_dir(index_dir)
        else:
            from queryquote.search_engine import SearchEngine

            engine = SearchEngine.from_index_dir(index_dir)

        # Try a test query
        test_queries = [
            "hello",
            "the",
            "movie",
        ]

        for query in test_queries:
            results = engine.search(query, top_k=3)
            print(f"  ✓ Query '{query}': {len(results)} results found")

            if results:
                top = results[0]
                print(f"    - Top result: {top.movie_id} (score: {top.score:.3f})")
                return True

        print(f"  ℹ️  No results found for test queries (index might be empty)")
        return False

    except Exception as e:
        print(f"  ❌ Search test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_flask_files() -> bool:
    """Check if Flask template and static files exist."""
    print(f"\n📦 Checking Flask files:")

    src_dir = Path(__file__).parent / "src" / "queryquote"
    templates_dir = src_dir / "templates"
    static_dir = src_dir / "static"

    if not templates_dir.exists():
        print(f"  ❌ Templates directory not found: {templates_dir}")
        return False

    index_html = templates_dir / "index.html"
    if not index_html.exists():
        print(f"  ❌ index.html not found in templates")
        return False

    print(f"  ✓ HTML template found")

    if not static_dir.exists():
        print(f"  ❌ Static directory not found: {static_dir}")
        return False

    print(f"  ✓ Static directory exists")

    app_js = static_dir / "app.js"
    if not app_js.exists():
        print(f"  ❌ app.js not found")
        return False

    print(f"  ✓ JavaScript files found")

    style_css = static_dir / "style.css"
    if not style_css.exists():
        print(f"  ❌ style.css not found")
        return False

    print(f"  ✓ CSS files found")

    return True


def main() -> None:
    """Run diagnostics."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Diagnose QueryQuote issues"
    )
    parser.add_argument(
        "--index-dir",
        default="data/index",
        help="Path to index directory (default: data/index)",
    )
    parser.add_argument(
        "--backend",
        default="sqlite",
        choices=["sqlite", "pickle"],
        help="Index backend (default: sqlite)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("QueryQuote Diagnostic Tool")
    print("=" * 60)

    # Run checks
    checks = [
        ("Flask files", lambda: check_flask_files()),
        ("Index", lambda: check_index(args.index_dir)),
        ("Search engine", lambda: check_search_engine(args.index_dir, args.backend)),
        ("Search functionality", lambda: test_search(args.index_dir, args.backend)),
    ]

    results = []
    for name, check in checks:
        try:
            result = check()
            results.append((name, result))
        except Exception as e:
            print(f"\n⚠️  Unexpected error in {name} check: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)

    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✨ All checks passed! The system should be working.")
        print("\nTo start the web server, run:")
        print(f"  python run_web.py --index-dir {args.index_dir}")
    else:
        print("\n⚠️  Some checks failed. See details above.")

    print("=" * 60)


if __name__ == "__main__":
    main()
