<!--
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 (IR Project)

Prologue:
Project-level README for QueryQuote setup, architecture, and day-to-day usage.

Last updated: 2026-04-27 - Updated backend launcher naming and documented the
installed queryquote/queryquote-web CLI workflow.
-->

```text
  /$$$$$$                                                 /$$$$$$                        /$$              
 /$$__  $$                                               /$$__  $$                      | $$              
| $$  \ $$ /$$   /$$  /$$$$$$   /$$$$$$  /$$   /$$      | $$  \ $$ /$$   /$$  /$$$$$$  /$$$$$$    /$$$$$$ 
| $$  | $$| $$  | $$ /$$__  $$ /$$__  $$| $$  | $$      | $$  | $$| $$  | $$ /$$__  $$|_  $$_/   /$$__  $$
| $$  | $$| $$  | $$| $$$$$$$$| $$  \__/| $$  | $$      | $$  | $$| $$  | $$| $$  \ $$  | $$    | $$$$$$$$
| $$/$$ $$| $$  | $$| $$_____/| $$      | $$  | $$      | $$/$$ $$| $$  | $$| $$  | $$  | $$ /$$| $$_____/
|  $$$$$$/|  $$$$$$/|  $$$$$$$| $$      |  $$$$$$$      |  $$$$$$/|  $$$$$$/|  $$$$$$/  |  $$$$/|  $$$$$$$
 \____ $$$ \______/  \_______/|__/       \____  $$       \____ $$$ \______/  \______/    \___/   \_______/
      \__/                               /$$  | $$            \__/                                        
                                        |  $$$$$$/                                                        
                                         \______/                                                         
```

# QueryQuote

QueryQuote is a movie-quote search engine for finding the film behind a remembered
line of dialogue. It is built as a Next.js frontend backed by a Python/Flask
information retrieval service that indexes the `movie-transcripts-59k` corpus.

The current system supports exact quote lookup, loose wording, missing
punctuation, and optional authority-based reranking using Metacritic vote counts.
The default web search path uses the v2 SQLite index, while the UI also exposes a
Legacy Search toggle for comparing against the v1 SQLite index.

## Tech Stack

- Frontend: Next.js 16 App Router, React 19, Tailwind CSS 4
- Backend: Python 3.10+ package with Flask
- Search storage: SQLite for v1 and v2 large-corpus search
- Retrieval: inverted positional indexes, BM25, TF-IDF cosine similarity, phrase
  matching, proximity scoring, and fuzzy quote reranking
- Dataset: `backend/movie-transcripts-59k/transcripts`

## Project Layout

```text
app/
  (home)/page.jsx                    Landing page
  (routes)/search/page.jsx           Search UI
  (routes)/how/page.jsx              Implementation guide page
  (routes)/transcripts/page.jsx      Reserved transcript browser route
  api/search/route.js                Next.js proxy to the Flask API
backend/
  BACKEND_README.md                  Backend-specific API and CLI documentation
  pyproject.toml                     Python package metadata
  app.py                             Direct Flask API launcher for source checkouts
  authority_compact.csv              Compact authority data for vote-count boosts
  data2_intersection/index.db        Official compact v2 index for authority-matched movies
  data2_rest/index.db                Official v2 index for the remaining corpus
  src/queryquote/                    Search, indexing, API, and evaluation code
  tests/                             Python regression tests
public/
  background.png and app icons
test/
  engine-comparisons/ and time-logs/ Local experiment outputs
```

Large generated indexes and the transcript corpus are intentionally ignored by
Git. If those folders are missing in a fresh checkout, rebuild the indexes from
the commands below after restoring the transcript dataset.

## Prerequisites

- Node.js and npm
- Python 3.10 or newer
- The transcript corpus at `backend/movie-transcripts-59k/transcripts`

This workspace has been run with Node `v23.7.0`, npm `11.12.1`, and Python
`3.13.7`, but the backend package declares support for Python 3.10+.

## Install

From the repository root:

```bash
npm install
```

Create and activate a Python virtual environment, then install the backend
package in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e backend
```

If the virtual environment already exists, activate it before running backend
commands:

```bash
source .venv/bin/activate
```

After installation, the backend exposes two commands:

```bash
queryquote --help
queryquote-web --help
```

If the editable install is not active, use
`PYTHONPATH=backend/src python3 -m queryquote.cli ...` as a source-checkout
fallback.

## Build Search Indexes

The frontend defaults to v2 search and sends `index_version: "v2"` through the
Next.js proxy. This project officially uses two v2 SQLite indexes so the app can
serve either a smaller, authority-matched corpus or the rest of the transcript
collection.

For Legacy Search comparisons, build a v1 SQLite index:

```bash
queryquote build \
  --backend sqlite \
  --data-dir backend/movie-transcripts-59k/transcripts \
  --output-dir backend/data/index \
  --progress-every-files 500
```

Build the compact v2 index for movies that matched the authority CSV. This is
the smaller but effective search option:

```bash
queryquote build-v2 \
  --data-dir backend/movie-transcripts-59k/transcripts \
  --output-dir backend/data2_intersection \
  --authority-csv backend/authority_compact.csv \
  --corpus-mode intersection \
  --progress-every-files 1000 \
  --batch-size 50000
```

Build the companion v2 index for the remaining non-authority-matched corpus:

```bash
queryquote build-v2 \
  --data-dir backend/movie-transcripts-59k/transcripts \
  --output-dir backend/data2_rest \
  --authority-csv backend/authority_compact.csv \
  --corpus-mode rest \
  --progress-every-files 1000 \
  --batch-size 50000
```

## Run Locally

Start the Flask backend from the repository root. This example loads v1 as the
legacy index and uses the compact authority-intersection v2 index as the default
frontend target:

```bash
queryquote-web \
  --index-dir backend/data/index \
  --v2-index-dir backend/data2_intersection \
  --default-index-version v2
```

To serve the rest-of-corpus v2 index instead, change `--v2-index-dir`:

```bash
queryquote-web \
  --index-dir backend/data/index \
  --v2-index-dir backend/data2_rest \
  --default-index-version v2
```

The API runs at `http://127.0.0.1:5000`.

In a second terminal, start the frontend:

```bash
npm run dev
```

Open `http://localhost:3000/search`.

## Search Behavior

The browser posts to `app/api/search/route.js`, which proxies to
`http://127.0.0.1:5000/api/search`. The proxy always requests Top 50 results.
The search page displays those results in two client-side pages of 25 results
each.

Search options:

- Authority Boost: sends `authority_filter: true` so movies with stronger
  Metacritic vote-count authority can receive a ranking boost.
- Legacy Search: sends `index_version: "v1"` instead of the default `"v2"`.

## Backend CLI Examples

Search v2 directly:

```bash
queryquote search \
  --backend sqlite-v2 \
  --index-dir backend/data2_intersection \
  --query "you can't handle the truth" \
  --top-k 50
```

Search the rest-of-corpus v2 index:

```bash
queryquote search \
  --backend sqlite-v2 \
  --index-dir backend/data2_rest \
  --query "you can't handle the truth" \
  --top-k 50
```

Search v1 directly:

```bash
queryquote search \
  --backend sqlite \
  --index-dir backend/data/index \
  --query "you can't handle the truth" \
  --top-k 50
```

Enable authority reranking:

```bash
queryquote search \
  --backend sqlite-v2 \
  --index-dir backend/data2_intersection \
  --query "you can't handle the truth" \
  --top-k 50 \
  --authority-filter
```

## Notes

- `backend/BACKEND_README.md` contains API payload details, backend-only setup,
  and more complete CLI documentation.
- `backend/movie-transcripts-59k/LICENSE.txt` governs the transcript dataset.
- The Next.js proxy currently uses the fixed backend URL
  `http://127.0.0.1:5000`; update `app/api/search/route.js` if the Flask port
  changes.
