<!--
Prologue:
Backend README for QueryQuote API, CLI, index storage, and testing workflows.
Last updated: 2026-04-27 - Updated launcher naming and installed CLI usage.
-->

# QueryQuote Backend

The QueryQuote backend is a Python information retrieval package plus an
API-only Flask service. It builds searchable indexes from movie transcript text,
serves quote search requests, and supports both the original v1 SQLite search
path and the newer v2 SQLite search path.

## What The Backend Provides

- CLI commands for building, searching, and evaluating indexes
- Flask endpoints for health checks and quote search
- SQLite-backed indexes for large transcript corpora
- Optional authority reranking using `authority_compact.csv`
- v1/v2 index selection for side-by-side search comparisons

## Backend Layout

```text
backend/
  pyproject.toml                  Python package metadata and dependencies
  app.py                          Direct Flask API launcher for source checkouts
  authority_compact.csv           Compact authority data for vote-count boosts
  data/index/index.db             Recommended v1 SQLite index location
  data2_intersection/index.db     Official compact v2 index for authority-matched movies
  data2_rest/index.db             Official v2 index for the remaining corpus
  src/queryquote/
    cli.py                        build, build-v2, search, and evaluate commands
    webapp.py                     Flask API app factory and routes
    db_index.py                   v1 SQLite index builder/search engine
    db_index_v2.py                v2 SQLite index builder/search engine
    passages.py                   Transcript discovery and passage splitting
    preprocessing.py              v1 tokenization and normalization
    analyzer_v2.py                v2 tokenization and term analysis
    ranking.py                    BM25, TF-IDF, and normalization helpers
    quote_matching.py             Phrase, proximity, and fuzzy quote matching
    authority.py                  Authority CSV parsing and score multipliers
    evaluation.py                 MAP, MRR, nDCG@K, precision, and recall
  tests/                          Backend regression tests
```

## Install

From the repository root, create and activate a virtual environment before
installing the backend package:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e backend
```

Or from inside `backend/`:

```bash
python -m pip install -e .
```

The package requires Python 3.10 or newer and currently depends on Flask.

After installation, use `queryquote` for indexing/search/evaluation and
`queryquote-web` for the Flask API. If the editable install is not active, use
`PYTHONPATH=backend/src python3 -m queryquote.cli ...` as a source-checkout
fallback.

## Build Indexes

### v2 SQLite Indexes

The project officially uses a split v2 setup. `data2_intersection` is the
smaller authority-matched index, which gives users a compact but effective search
option. `data2_rest` is the companion index for the remaining corpus.

Build the compact authority-intersection index:

```bash
queryquote build-v2 \
  --data-dir backend/movie-transcripts-59k/transcripts \
  --output-dir backend/data2_intersection \
  --authority-csv backend/authority_compact.csv \
  --corpus-mode intersection \
  --progress-every-files 1000 \
  --batch-size 50000
```

Build the rest-of-corpus index:

```bash
queryquote build-v2 \
  --data-dir backend/movie-transcripts-59k/transcripts \
  --output-dir backend/data2_rest \
  --authority-csv backend/authority_compact.csv \
  --corpus-mode rest \
  --progress-every-files 1000 \
  --batch-size 50000
```

### v1 SQLite Index

Build v1 when you want the Legacy Search toggle or CLI comparisons:

```bash
queryquote build \
  --backend sqlite \
  --data-dir backend/movie-transcripts-59k/transcripts \
  --output-dir backend/data/index \
  --progress-every-files 500
```

## Run The API

From the repository root, start Flask with both v1 and v2 available. This
example serves the compact authority-intersection index as the v2 search path:

```bash
queryquote-web \
  --index-dir backend/data/index \
  --v2-index-dir backend/data2_intersection \
  --default-index-version v2
```

To serve the rest-of-corpus index instead:

```bash
queryquote-web \
  --index-dir backend/data/index \
  --v2-index-dir backend/data2_rest \
  --default-index-version v2
```

Default address: `http://127.0.0.1:5000`

Useful options:

- `--index-dir`: required primary index directory
- `--v2-index-dir`: optional v2 index directory loaded alongside v1
- `--default-index-version`: `v1` or `v2`; defaults to `v1` if omitted
- `--backend`: `sqlite`, `sqlite-v1`, or `sqlite-v2`
- `--host`: defaults to `127.0.0.1`
- `--port`: defaults to `5000`
- `--debug`: enables Flask debug mode

Run only the compact v2 index:

```bash
queryquote-web \
  --backend sqlite-v2 \
  --index-dir backend/data2_intersection \
  --default-index-version v2
```

## API Endpoints

### `GET /`

Returns service metadata, available index versions, the default index version,
and endpoint paths.

Example response:

```json
{
  "service": "queryquote-api",
  "status": "ok",
  "default_index_version": "v2",
  "available_index_versions": ["v1", "v2"],
  "endpoints": {
    "health": "/api/health",
    "search": "/api/search"
  }
}
```

### `GET /api/health`

Returns a lightweight health check:

```json
{
  "status": "ok",
  "default_index_version": "v2",
  "available_index_versions": ["v1", "v2"]
}
```

### `POST /api/search`

Searches indexed transcript passages.

Request body:

```json
{
  "query": "you can't handle the truth",
  "top_k": 50,
  "authority_filter": false,
  "index_version": "v2"
}
```

Fields:

- `query`: required quote text
- `top_k`: optional result count; defaults to 50
- `authority_filter`: optional boolean; defaults to `false`
- `index_version`: optional `v1` or `v2`; defaults to the server's configured
  default index version

Successful response:

```json
{
  "query": "you can't handle the truth",
  "index_version": "v2",
  "authority_filter": false,
  "results": [
    {
      "passage_id": "Movie Title _1992_::p0001",
      "movie_id": "Movie Title _1992_",
      "score": 1.2345,
      "snippet": "The matching transcript passage...",
      "source_file": "backend/movie-transcripts-59k/transcripts/Movie Title _1992_ - full transcript.txt"
    }
  ],
  "count": 1
}
```

Invalid requests return JSON with `error`, `results: []`, and `count: 0`.

## CLI Search

Search v2:

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

Search v1:

```bash
queryquote search \
  --backend sqlite \
  --index-dir backend/data/index \
  --query "you can't handle the truth" \
  --top-k 50
```

Search with authority reranking:

```bash
queryquote search \
  --backend sqlite-v2 \
  --index-dir backend/data2_intersection \
  --query "you can't handle the truth" \
  --top-k 50 \
  --authority-filter
```

You can also select v2 through the generic SQLite backend:

```bash
queryquote search \
  --backend sqlite \
  --index-version v2 \
  --index-dir backend/data2_intersection \
  --query "you can't handle the truth"
```

## Evaluation

The evaluator expects JSONL query and relevance files:

- Queries: one JSON object per line with `qid` and `query`
- Qrels: one JSON object per line with `qid`, `doc_id`, and optional
  `relevance`

Example command:

```bash
queryquote evaluate \
  --backend sqlite-v2 \
  --index-dir backend/data2_intersection \
  --queries path/to/queries.jsonl \
  --qrels path/to/qrels.jsonl \
  --top-k 50
```

The output includes MAP, MRR, nDCG@K, Precision@K, and Recall@K.

## Frontend Contract

The Next.js app calls its own server route at `/api/search`. That route proxies
requests to `http://127.0.0.1:5000/api/search`.

Current frontend behavior:

- Default search sends `index_version: "v2"`
- Legacy Search sends `index_version: "v1"`
- Authority Boost sends `authority_filter: true`
- The frontend requests 50 results and paginates them into two pages of 25

If the Flask server runs on a different host or port, update
`app/api/search/route.js`.

## Testing

Run backend tests from the repository root:

```bash
python -m pytest backend/tests
```

The tests cover:

- v2 phrase and relaxed phrase matching
- API selection between v1 and v2 indexes
- authority multiplier parsing and reranking

## Generated Files And Data

These paths are generated or local-data heavy and are ignored by Git:

- `backend/movie-transcripts-59k/`
- `backend/data/`
- `backend/data2/`
- `backend/data2_intersection/`
- `backend/data2_rest/`
- Python caches, virtual environments, and egg-info metadata

Keep source changes in `backend/src/queryquote/` and tests in `backend/tests/`.
