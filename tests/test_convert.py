import json

import pyarrow.parquet as pq

from dropatlas.convert import convert_dump


def test_convert_quarantines_bad_records_and_reports(nasty_releases, tmp_path):
    out = tmp_path / "landing" / "snapshot=2026-10-01"
    summary = convert_dump(nasty_releases, out, "releases")

    assert summary["records_seen"] == 4
    assert summary["rows_written"] == 3
    assert summary["bad_records"] == 1
    assert summary["control_bytes_removed"] == 1

    table = pq.read_table(out)  # reads every part file; "_" files are ignored
    assert table.num_rows == 3
    assert sorted(table.column("release_id").to_pylist()) == [101, 102, 103]

    bad = [json.loads(line) for line in (out / "_bad_records.jsonl").read_text().splitlines()]
    assert bad[0]["id"] == "not-a-number"
    assert not out.with_name(out.name + ".partial").exists()


def test_rerun_replaces_output_instead_of_appending(nasty_releases, tmp_path):
    out = tmp_path / "snap"
    convert_dump(nasty_releases, out, "releases")
    convert_dump(nasty_releases, out, "releases")
    assert pq.read_table(out).num_rows == 3


def test_limit_stops_early(nasty_releases, tmp_path):
    summary = convert_dump(nasty_releases, tmp_path / "snap", "releases", limit=2)
    assert summary["rows_written"] == 2
