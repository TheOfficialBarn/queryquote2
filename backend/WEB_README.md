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

3. Start the API server:

```bash
python run_web.py --index-dir data/index
```

Default server address: `http://127.0.0.1:5000`

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
