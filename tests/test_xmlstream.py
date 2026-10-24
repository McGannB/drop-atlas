import io

from dropatlas.xmlstream import CleanReader, iter_records, open_dump


def test_clean_reader_drops_control_bytes():
    reader = CleanReader(io.BytesIO(b"<a>ok\x0b\x01text\ttab</a>"))
    assert reader.read() == b"<a>oktext\ttab</a>"
    assert reader.removed == 2


def test_clean_reader_does_not_fake_end_of_file():
    # The first 3-byte chunk is all control bytes; the reader must keep going.
    reader = CleanReader(io.BytesIO(b"\x01\x02\x03<a/>"))
    assert reader.read(3) == b"<a/"  # data, not b"" (which the parser would treat as the end)
    assert reader.read(3) == b">"


def test_only_top_level_records_are_yielded(nasty_labels):
    ids = [elem.findtext("id") for elem in iter_records(open_dump(nasty_labels), "label")]
    assert ids == ["501", "601"]  # the two <label> tags inside <sublabels> are not records


def test_gzip_dump_with_control_byte_parses(nasty_releases):
    stream = open_dump(nasty_releases)
    ids = [elem.get("id") for elem in iter_records(stream, "release")]
    assert ids == ["101", "102", "103", "not-a-number"]
    assert stream.removed == 1


# --- Starting a fresh parser every segment (Windows' parser stops at 2 GiB) ---

MANY = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n<labels>\n'
    + b"".join(
        b"<label><id>%d</id><name>L %d &gt; x</name>"
        b'<sublabels><label id="%d">Sub</label></sublabels></label>\n' % (i, i, i + 10_000)
        for i in range(1, 3001)
    )
    + b"</labels>\n"
)


def _ids(stream, **kwargs):
    return [e.findtext("id") for e in iter_records(stream, "label", **kwargs)]


def test_new_parser_every_segment_gives_the_same_records(caplog):
    caplog.set_level("INFO", logger="dropatlas.xmlstream")
    expected = [str(i) for i in range(1, 3001)]
    assert _ids(io.BytesIO(MANY)) == expected
    # Tiny segments and odd chunk sizes force hundreds of parser restarts mid-chunk.
    assert _ids(io.BytesIO(MANY), segment_bytes=500, chunk_bytes=777) == expected
    assert sum("starting XML parser" in m for m in caplog.messages) > 100


def test_header_split_across_chunks():
    assert _ids(io.BytesIO(MANY), segment_bytes=2000, chunk_bytes=7)[:3] == ["1", "2", "3"]


def test_segments_keep_nested_records_out(nasty_labels):
    assert _ids(open_dump(nasty_labels), segment_bytes=1) == ["501", "601"]


def test_random_chunks_and_segments_never_lose_or_split_a_record():
    import random

    rng = random.Random(7)
    expected = [str(i) for i in range(1, 3001)]
    for _ in range(25):
        kwargs = {"segment_bytes": rng.randint(1, 60_000), "chunk_bytes": rng.randint(1, 9_000)}
        assert _ids(io.BytesIO(MANY), **kwargs) == expected, kwargs
