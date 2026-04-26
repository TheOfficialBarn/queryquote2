"""Prologue:
Smoke tests for the in-memory QueryQuote search engine.
Last updated: 2026-04-25 - Added coverage for the opt-in authority filter so
default ranking remains unchanged unless the filter is enabled.
"""

from queryquote.authority import build_authority_index
from queryquote.indexing import IndexBundle, build_index
from queryquote.search_engine import SearchEngine
from queryquote.types import Passage


def test_smoke_search_returns_expected_movie():
    passages = [
        Passage(
            passage_id="m1::p0000",
            movie_id="Movie A",
            source_file="a.txt",
            raw_text="you cant handle the truth",
        ),
        Passage(
            passage_id="m2::p0000",
            movie_id="Movie B",
            source_file="b.txt",
            raw_text="may the force be with you",
        ),
    ]
    bundle = IndexBundle(index=build_index(passages), passages=passages)
    engine = SearchEngine(bundle=bundle)
    results = engine.search("you cant handle the truth", top_k=1)
    assert results
    assert results[0].movie_id == "Movie A"


def test_authority_filter_is_opt_in_and_reorders_equal_matches():
    passages = [
        Passage(
            passage_id="Low Vote Movie _2020_::p0000",
            movie_id="Low Vote Movie _2020_",
            source_file="low.txt",
            raw_text="shared quote text",
        ),
        Passage(
            passage_id="High Vote Movie _2020_::p0000",
            movie_id="High Vote Movie _2020_",
            source_file="high.txt",
            raw_text="shared quote text",
        ),
    ]
    authority_index = build_authority_index(
        [
            {
                "Title": "Low Vote Movie",
                "Release Date": "Jan 1, 2020",
                "No of Persons Voted": "3",
            },
            {
                "Title": "High Vote Movie",
                "Release Date": "Jan 1, 2020",
                "No of Persons Voted": "3,000",
            },
        ]
    )
    bundle = IndexBundle(index=build_index(passages), passages=passages)
    engine = SearchEngine(bundle=bundle, authority_index=authority_index)

    unfiltered_results = engine.search("shared quote text", top_k=2)
    unfiltered_scores = {result.movie_id: result.score for result in unfiltered_results}

    filtered_results = engine.search("shared quote text", top_k=2, authority_filter=True)
    filtered_scores = {result.movie_id: result.score for result in filtered_results}

    assert unfiltered_scores["Low Vote Movie _2020_"] == unfiltered_scores[
        "High Vote Movie _2020_"
    ]
    assert filtered_scores["High Vote Movie _2020_"] > filtered_scores[
        "Low Vote Movie _2020_"
    ]
    assert filtered_results[0].movie_id == "High Vote Movie _2020_"
