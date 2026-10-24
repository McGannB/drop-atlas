import hashlib

from dropatlas.fetch import discogs_name, discogs_url, parse_checksums, sha256_of


def test_discogs_names_and_urls():
    assert discogs_name("2026-10", "releases") == "discogs_20261001_releases.xml.gz"
    assert discogs_name("2026-10", "CHECKSUM") == "discogs_20261001_CHECKSUM.txt"
    assert discogs_url("2026-10", "labels").endswith("data%2F2026%2Fdiscogs_20261001_labels.xml.gz")


def test_parse_checksums():
    text = (
        "a" * 64
        + " discogs_20261001_artists.xml.gz\n"
        + "B" * 64
        + "  *discogs_20261001_labels.xml.gz\n"
        + "not a checksum line\n"
    )
    assert parse_checksums(text) == {
        "discogs_20261001_artists.xml.gz": "a" * 64,
        "discogs_20261001_labels.xml.gz": "b" * 64,
    }


def test_sha256_of(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"drop atlas")
    assert sha256_of(path) == hashlib.sha256(b"drop atlas").hexdigest()
