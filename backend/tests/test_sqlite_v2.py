"""
Authors: Aiden Barnard & Atharva
Class: EECS 767 IR (Class Project)

Prologue:
Regression coverage for v1/v2 SQLite backend selection and v2 search.
Last updated: 2026-04-27 - Added relaxed phrase coverage for v2 ranking when
small wording differences would otherwise break full exact-phrase matching.
"""

from queryquote.db_index import build_sqlite_index
from queryquote.db_index_v2 import build_sqlite_index_v2
from queryquote.webapp import create_app


def _write_transcript(data_dir, movie_id: str, text: str) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / f"{movie_id} - full transcript.txt").write_text(text, encoding="utf-8")


def test_sqlite_v2_search_finds_phrase_match(tmp_path):
    data_dir = tmp_path / "transcripts"
    _write_transcript(
        data_dir,
        "The Testfather _1972_",
        "Someday I am going to make him an offer he can not refuse.",
    )
    _write_transcript(
        data_dir,
        "Space Quote _1977_",
        "May the force be with you while the rebels escape.",
    )

    index_dir = tmp_path / "v2"
    build_sqlite_index_v2(
        data_dir=data_dir,
        output_dir=index_dir,
        max_passage_tokens=16,
        passage_overlap=4,
        authority_csv_path=tmp_path / "missing-authority.csv",
    )

    app = create_app(str(index_dir), backend="sqlite-v2")
    response = app.test_client().post(
        "/api/search",
        json={
            "query": "make him an offer he cannot refuse",
            "index_version": "v2",
            "top_k": 1,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["index_version"] == "v2"
    assert payload["results"][0]["movie_id"] == "The Testfather _1972_"


def test_sqlite_v2_relaxed_phrase_handles_small_wording_differences(tmp_path):
    data_dir = tmp_path / "transcripts"
    _write_transcript(
        data_dir,
        "Chocolate Source _1994_",
        "My mama always said life was like a box of chocolates you never know what you are going to get.",
    )
    _write_transcript(
        data_dir,
        "Chocolate Distractor _2020_",
        "Life can feel strange when people like a box and know where chocolates get stored.",
    )

    index_dir = tmp_path / "v2"
    build_sqlite_index_v2(
        data_dir=data_dir,
        output_dir=index_dir,
        max_passage_tokens=20,
        passage_overlap=4,
        authority_csv_path=tmp_path / "missing-authority.csv",
    )

    app = create_app(str(index_dir), backend="sqlite-v2")
    response = app.test_client().post(
        "/api/search",
        json={
            "query": "life is like a box of chocolates you never know what you are going to get",
            "index_version": "v2",
            "top_k": 1,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["results"][0]["movie_id"] == "Chocolate Source _1994_"


def test_backend_can_select_v1_and_v2_indexes(tmp_path):
    data_dir = tmp_path / "transcripts"
    _write_transcript(
        data_dir,
        "Legacy Winner _2001_",
        "shared quote text appears in the legacy and v2 index",
    )

    v1_dir = tmp_path / "v1"
    v2_dir = tmp_path / "v2"
    build_sqlite_index(
        data_dir=data_dir,
        output_dir=v1_dir,
        max_passage_tokens=12,
        passage_overlap=2,
    )
    build_sqlite_index_v2(
        data_dir=data_dir,
        output_dir=v2_dir,
        max_passage_tokens=12,
        passage_overlap=2,
        authority_csv_path=tmp_path / "missing-authority.csv",
    )

    app = create_app(str(v1_dir), backend="sqlite", v2_index_dir=str(v2_dir))
    client = app.test_client()

    v1_response = client.post(
        "/api/search",
        json={"query": "shared quote text", "index_version": "v1", "top_k": 1},
    )
    v2_response = client.post(
        "/api/search",
        json={"query": "shared quote text", "index_version": "v2", "top_k": 1},
    )

    assert v1_response.status_code == 200
    assert v2_response.status_code == 200
    assert v1_response.get_json()["index_version"] == "v1"
    assert v2_response.get_json()["index_version"] == "v2"
    assert v1_response.get_json()["results"][0]["movie_id"] == "Legacy Winner _2001_"
    assert v2_response.get_json()["results"][0]["movie_id"] == "Legacy Winner _2001_"
