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
