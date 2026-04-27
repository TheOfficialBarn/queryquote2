# QueryQuote API Server

This backend is an API-only Flask service for QueryQuote search.

## Quick Start

1. Install dependencies:

```bash
pip install -e .
```

2. Build an index (one-time per dataset):

```bash
queryquote build --data-dir movie-transcripts-59k/transcripts --output-dir data/index
```

3. Start the API server (Make sure you are in root directory (e.g. `QueryQuote/`)):

```bash
python run_web.py \
--index-dir backend/indexes/v1 \
--v2-index-dir backend/indexes/v2
```

Default server address: `http://127.0.0.1:5000`

If modified, be sure that the front-end is configured to query the correct `URL` & `port number` 

## API Endpoints
- `GET /` basic service metadata
- `GET /api/health` health check
- `POST /api/search` search endpoint

### Search Request

```json
{
  "query": "your search query",
  "top_k": 50,
  "authority_filter": false
}
```

`authority_filter` is optional and defaults to `false`. When set to `true`,
ranked movies found in `authority.csv` are adjusted by Metacritic vote count:
sparse-vote movies are lowered and high-vote movies are boosted.

### Search Response

```json
{
  "query": "your search query",
  "results": [
    {
      "passage_id": "movie_id::p1",
      "movie_id": "Movie Title",
      "score": 0.95,
      "snippet": "The full quote text...",
      "source_file": "Movie_Title_2021_-_full_transcript.txt"
    }
  ],
  "count": 1
}
```

## Useful Run Options

- `--index-dir` required
- `--host` default `127.0.0.1`
- `--port` default `5000`
- `--backend` `sqlite` (default) or `pickle`
- `--debug` enable Flask debug mode

## Frontend Integration

Your Next.js app can call `POST http://127.0.0.1:5000/api/search` from:

- a Next.js server route (`app/api/.../route.js`), or
- client-side code if CORS is configured.

Using a Next.js server route/proxy is usually simplest because it avoids browser CORS issues.




<!-- FROM README.MD -->
# QueryQuote

QueryQuote is a Python information retrieval project for finding movies by remembered quotes, including partial or slightly incorrect quotes.

## Implemented Baselines

- Inverted positional index over passage text
- TF-IDF + cosine similarity ranking
- BM25 ranking
- Quote-specific reranking:
  - phrase matching
  - proximity scoring
  - fuzzy matching for misquotes and misspellings
- Evaluation metrics:
  - MAP
  - MRR
  - nDCG@K
  - Precision@K / Recall@K

## Project Layout

```
src/queryquote/
  cli.py
  config.py
  evaluation.py
  indexing.py
  passages.py
  preprocessing.py
  quote_matching.py
  ranking.py
  search_engine.py
  types.py
examples/
  queries.jsonl
  qrels.jsonl
tests/
```

## Quick Start

From the workspace root:

```bash
python -m pip install -e .
```

Build index from transcripts:

```bash
queryquote build --data-dir movie-transcripts-59k/transcripts --output-dir data/index
```

Run search:

```bash
queryquote search --index-dir data/index --query "you can't handle the truth" --top-k 50
```

Run evaluation with starter files:

```bash
queryquote evaluate --index-dir data/index --queries examples/queries.jsonl --qrels examples/qrels.jsonl --top-k 50
```

## Notes

- Passage indexing defaults to sliding token windows to balance recall and precision.
- Punctuation is normalized away before indexing and searching.
- Fuzzy matching is applied only to top candidates for efficiency.

## Storage Backends

QueryQuote supports two index storage backends:

- sqlite (recommended for large corpora)
  - streaming build with periodic progress logs
  - writes reusable data/index/index.db
  - avoids all-or-nothing final serialization behavior
- pickle (legacy)
  - writes data/index/index_bundle.pkl
  - keeps more data in memory during build

For the 59k transcript corpus, prefer sqlite.

## Large-Corpus Commands (Recommended)

Build with sqlite backend:

```bash
queryquote build --backend sqlite --data-dir movie-transcripts-59k/transcripts --output-dir data/index --progress-every-files 500
```

Search using sqlite backend:

```bash
queryquote search --backend sqlite --index-dir data/index --query "you can't handle the truth" --top-k 50
```

Enable optional authority reranking with Metacritic vote counts:

```bash
queryquote search --backend sqlite --index-dir data/index --query "you can't handle the truth" --top-k 50 --authority-filter
```

Evaluate using sqlite backend:

```bash
queryquote evaluate --backend sqlite --index-dir data/index --queries examples/queries.jsonl --qrels examples/qrels.jsonl --top-k 50
```

<!-- BUILDING THE INDEXES -->
<!-- NOTE THAT LEGACY IS DEPRECATED -->
```
PYTHONPATH=backend/src python3 -m queryquote.cli build-v2 \
  --data-dir backend/movie-transcripts-59k/transcripts \
  --output-dir backend/data2_intersection \
  --authority-csv backend/authority_compact.csv \
  --corpus-mode intersection \
  --progress-every-files 1000 \
  --batch-size 50000
```

```
PYTHONPATH=backend/src python3 -m queryquote.cli build-v2 \
  --data-dir backend/movie-transcripts-59k/transcripts \
  --output-dir backend/data2_rest \
  --authority-csv backend/authority_compact.csv \
  --corpus-mode rest \
  --progress-every-files 1000 \
  --batch-size 50000
```