"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Shared configuration values for QueryQuote indexing, ranking, and search defaults.

Last updated: 2026-04-26 - Raised the default search result count to Top 50
to support two-page search results without user-selectable Top K controls.
"""

from __future__ import annotations
from dataclasses import dataclass

# Default passage size during indexing
# When transcripts are split into chunks, each passage is usually up to 120 tokens
# Used by: cli.py for build/build-v2
# Used by: db_index_v2.py as default build setting
DEFAULT_MAX_PASSAGE_TOKENS = 120

# Default overlap between consectutive passages
# Used by: cli.py
# Used by: db_index_v2.py
DEFAULT_PASSAGE_OVERLAP = 20

# Default number of search results to return
# Used by: cli.py
# Used by: webapp.py (API search endpoint)
# Used by: db_index.py
# Used by: db_index_v2.py
# 
# This is active and important because the frontend/API defaults to 50 results 
# unless the request overrides top_k.
DEFAULT_TOP_K = 50
