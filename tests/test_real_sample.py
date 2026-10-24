"""Regression test on 200 real Discogs releases (made in Lab 1.9 with `dropatlas discogs-sample`)."""

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from dropatlas.convert import convert_dump

SAMPLE = Path(__file__).parent / "fixtures" / "releases_real_sample.xml.gz"


@pytest.mark.skipif(not SAMPLE.exists(), reason="make the fixture in Lab 1.9 first")
def test_real_sample_converts_cleanly(tmp_path):
    summary = convert_dump(SAMPLE, tmp_path / "out", "releases")
    assert summary["rows_written"] == 200
    assert summary["bad_records"] == 0
    table = pq.read_table(tmp_path / "out")
    assert table.column("release_id").null_count == 0
    assert len(set(table.column("release_id").to_pylist())) == 200
