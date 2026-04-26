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
queryquote search --index-dir data/index --query "you can't handle the truth" --top-k 10
```

Run evaluation with starter files:

```bash
queryquote evaluate --index-dir data/index --queries examples/queries.jsonl --qrels examples/qrels.jsonl --top-k 10
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
queryquote search --backend sqlite --index-dir data/index --query "you can't handle the truth" --top-k 10
```

Enable optional authority reranking with Metacritic vote counts:

```bash
queryquote search --backend sqlite --index-dir data/index --query "you can't handle the truth" --top-k 10 --authority-filter
```

Evaluate using sqlite backend:

```bash
queryquote evaluate --backend sqlite --index-dir data/index --queries examples/queries.jsonl --qrels examples/qrels.jsonl --top-k 10
```
