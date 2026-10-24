from datetime import date

from dropatlas.discogs import parse_label, parse_release
from dropatlas.xmlstream import iter_records, open_dump


def _releases(path):
    return {
        e.get("id"): parse_release(e)
        for e in iter_records(open_dump(path), "release")
        if e.get("id").isdigit()
    }


def test_release_level_credits_only(nasty_releases):
    first = _releases(nasty_releases)["101"]
    assert [a["artist_id"] for a in first["artists"]] == [9001, 9002]
    assert first["artists"][0]["join_phrase"] == "&"
    assert first["extra_artists"][0]["role"] == "Mastered By"
    assert first["track_count"] == 2


def test_release_fields(nasty_releases):
    rows = _releases(nasty_releases)
    assert rows["101"]["styles"] == ["Dubstep", "Future Bass"]
    assert rows["101"]["labels"] == [{"label_id": 501, "name": "Ophelia Records", "catno": "OPH001"}]
    assert rows["101"]["released_date"] == date(2019, 3, 15)
    assert rows["102"]["title"] == "BrokenTitle"
    assert rows["102"]["released_date"] is None
    assert rows["103"]["released_precision"] == "year"
    assert rows["103"]["master_id"] == 7001
    assert rows["103"]["is_main_release"] is True
    assert rows["102"]["is_main_release"] is False


def test_label_parent_and_sublabels(nasty_labels):
    labels = [parse_label(e) for e in iter_records(open_dump(nasty_labels), "label")]
    assert labels[0]["sublabel_ids"] == [601, 602]
    assert labels[1]["parent_label_id"] == 501
