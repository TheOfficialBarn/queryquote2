"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
This file is the shared "data shape" file for QueryQuote.
It defines small dataclasses that other modules pass around.
This is what we use instead of loose dictionaries or tuples
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(slots=True)
class Passage:
    passage_id: str         # E.g. Movie Name::p0003
    movie_id: str           # Derived from the transcript filename
    source_file: str        # Path to transcript file
    raw_text: str           # Actual passage text getting indexed


@dataclass(slots=True)
class SearchResult:
    passage_id: str         # ID of the matched passage
    movie_id: str           # Movie the passage belongs to
    score: float            # Ranking score after query matching (& optional authority filtering)
    snippet: str            # Shortened preview of passage text: first 220 chars (MAY NEED TO CHANGE)
    source_file: str        # Transcript file path for traceability/debugging


# QREL is currently defined but **NOT USED** as a dataclass
# evaluation.py has something similar stored in dictionary,
# so this may be useful to refer to for more info

# Evaluation.py loads QRELS into a nested dictionary instead
# "For query X, is doc/passage Y relevant, and how relevant is it?"
# In this codebase this is treated as binary (either relevant or not),
# but with extra measures just incase
# 0 = not relevant;
# 1 = relevant
# 2 = also relevant (just incase)
# 3 = also relevant (just incase)
@dataclass(slots=True)
class Qrel:                 # Query relevance judgement: expected relevance label used for IR evaluation
    qid: str                # query ID from the evaluation query set
    doc_id: str             # Relevant passage/document ID
    relevance: int          # Relevance grade (typically 0 or positive)
