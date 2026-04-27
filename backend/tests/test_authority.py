"""
Authors: Aiden Barnard & Atharva Patil
Class: EECS 767 IR (Class Project)

Prologue:
Regression coverage for authority vote-count parsing and movie matching.
Last updated: 2026-04-27 - Added import comments explaining the authority
index builder dependency under test.
"""

from queryquote.authority import build_authority_index  # Builds in-memory authority indexes for multiplier assertions.


def test_authority_index_maps_votes_to_bounded_movie_multipliers():
    index = build_authority_index(
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

    low_multiplier = index.multiplier_for_movie_id("Low Vote Movie _2020_")
    high_multiplier = index.multiplier_for_movie_id("High Vote Movie _2020_")

    assert low_multiplier is not None
    assert high_multiplier is not None
    assert 0.75 <= low_multiplier < 1.0
    assert 1.0 < high_multiplier <= 1.25
    assert index.multiplier_for_movie_id("Missing Movie _2020_") is None
