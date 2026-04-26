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