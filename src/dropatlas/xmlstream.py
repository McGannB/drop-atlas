"""Stream records out of huge XML dumps without loading them into memory."""

from __future__ import annotations

import gzip
import logging
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

log = logging.getLogger(__name__)

# Control characters that XML 1.0 forbids. Tab, newline and carriage return are allowed.
BAD_BYTES = bytes(b for b in range(0x20) if b not in (0x09, 0x0A, 0x0D))

# Python's XML parser on Windows stops after 2 GiB of input ("out of memory"), so we
# start a fresh parser about every 1 GiB, cutting the stream exactly between two records.
SEGMENT_BYTES = 1 << 30
CHUNK_BYTES = 1 << 16


class CleanReader:
    """Wrap a binary stream and drop the control bytes the XML parser refuses.

    Safe for UTF-8: bytes below 0x20 never appear inside a multi-byte character.
    """

    def __init__(self, raw):
        self.raw = raw
        self.removed = 0

    def read(self, size: int = -1) -> bytes:
        while True:
            chunk = self.raw.read(size)
            if not chunk:
                return b""
            cleaned = chunk.translate(None, BAD_BYTES)
            self.removed += len(chunk) - len(cleaned)
            if cleaned:  # a chunk made only of bad bytes is not the end of the file
                return cleaned

    def close(self) -> None:
        self.raw.close()


def open_dump(path: str | Path) -> CleanReader:
    """Open a .xml or .xml.gz dump as a cleaned byte stream."""
    path = Path(path)
    raw = gzip.open(path, "rb") if path.suffix == ".gz" else open(path, "rb")
    return CleanReader(raw)


class _Position:
    """Where the current parser is in the document."""

    def __init__(self):
        self.depth = 0
        self.root = None
        self.between_records = False


def _finished_records(parser: ET.XMLPullParser, tag: str, pos: _Position) -> Iterator[ET.Element]:
    """Yield top-level <tag> elements the parser has finished, then free them."""
    for event, elem in parser.read_events():
        if event == "start":
            if pos.root is None:
                pos.root = elem
            pos.depth += 1
            continue
        pos.depth -= 1
        if pos.depth == 1:  # a direct child of the root just closed
            pos.between_records = True
            if elem.tag == tag:
                yield elem
            pos.root.clear()  # drop the finished record so memory stays flat


def iter_records(
    stream, tag: str, segment_bytes: int = SEGMENT_BYTES, chunk_bytes: int = CHUNK_BYTES
) -> Iterator[ET.Element]:
    """Yield each top-level <tag> element (a direct child of the root), then free it.

    Nested elements with the same tag (a <label> inside <sublabels>) are skipped,
    because only elements that close at depth 1 are records.
    """
    header = b""  # the start of the document up to and including the root start tag
    captured = b""  # the header while we're still reading it
    root_end = b""  # the matching closing tag, e.g. b"</releases>"
    pending = b""  # bytes read from the stream but not fed to a parser yet
    segment = 0
    total = 0
    finished = False

    while not finished:
        parser = ET.XMLPullParser(events=("start", "end"))
        pos = _Position()
        fed = 0
        if header:  # every parser after the first gets the document's opening again
            parser.feed(header)
            fed = len(header)
            yield from _finished_records(parser, tag, pos)
        segment += 1
        start_new = False

        while not start_new:
            chunk, pending = (pending or stream.read(chunk_bytes)), b""
            if not chunk:
                finished = True
                break
            if header and fed < segment_bytes:  # normal case: feed the whole chunk
                parser.feed(chunk)
                fed += len(chunk)
                total += len(chunk)
                yield from _finished_records(parser, tag, pos)
                continue

            # Careful mode (the header, or time for a new parser): feed up to each ">"
            # so we know exactly which byte an element ended on. First let the parser
            # catch up on everything already fed, so old events can't look new.
            parser.flush()  # Python 3.12.3+
            yield from _finished_records(parser, tag, pos)
            i = 0
            while i < len(chunk):
                gt = chunk.find(b">", i)
                end = len(chunk) if gt < 0 else gt + 1
                piece = chunk[i:end]
                parser.feed(piece)
                fed += len(piece)
                total += len(piece)
                i = end
                if not header:
                    captured += piece
                parser.flush()  # parse every byte fed so far (Python 3.12.3+), so events line up
                pos.between_records = False
                yield from _finished_records(parser, tag, pos)

                if not header and pos.root is not None:  # we just fed the root start tag
                    header, pending = captured, chunk[i:]
                    name = re.search(rb"<([^\s/>?!]+)[^<]*>\s*$", header).group(1)
                    root_end = b"</" + name + b">"
                    break
                if header and fed >= segment_bytes and pos.between_records:
                    pending = chunk[i:]  # the rest belongs to the next parser
                    start_new = True
                    break

        if start_new:  # close this parser cleanly, as if the document ended here
            parser.feed(root_end)
            log.info("starting XML parser #%d after %.1f GB", segment + 1, total / 1e9)
        parser.close()
        yield from _finished_records(parser, tag, pos)
