"""Convert a Discogs XML dump into Parquet files plus a run summary."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from . import schemas
from .discogs import parse_artist, parse_label, parse_release
from .writer import ChunkedParquetWriter, PartialDir, write_summary
from .xmlstream import iter_records, open_dump

log = logging.getLogger(__name__)

KINDS = {
    "releases": ("release", parse_release, schemas.RELEASE),
    "artists": ("artist", parse_artist, schemas.ARTIST),
    "labels": ("label", parse_label, schemas.LABEL),
}


def convert_dump(src: str | Path, out_dir: str | Path, kind: str, limit: int | None = None) -> dict:
    tag, parse, schema = KINDS[kind]
    started = time.monotonic()
    seen = bad = 0
    stream = open_dump(src)
    with PartialDir(out_dir) as work:
        bad_path = work / "_bad_records.jsonl"
        with ChunkedParquetWriter(work, schema) as writer, open(bad_path, "w", encoding="utf-8") as bad_file:
            for elem in iter_records(stream, tag):
                seen += 1
                try:
                    row = parse(elem)
                except MemoryError:
                    raise  # a full machine isn't a bad record: stop the run
                except Exception as exc:  # quarantine the record, keep the run going
                    bad += 1
                    record_id = elem.get("id") or elem.findtext("id")
                    bad_file.write(json.dumps({"id": record_id, "error": repr(exc)}) + "\n")
                else:
                    writer.write(row)  # outside the try: a Parquet error should stop the run
                if seen % 250_000 == 0:
                    log.info("%s: %s records, %.0fs", kind, f"{seen:,}", time.monotonic() - started)
                if limit and seen >= limit:
                    break
        stream.close()
        summary = {
            "kind": kind,
            "source_file": Path(src).name,
            "records_seen": seen,
            "rows_written": writer.rows,
            "bad_records": bad,
            "control_bytes_removed": stream.removed,
            "files": len(writer.files),
            "seconds": round(time.monotonic() - started, 1),
            "limit": limit,
            "finished_at": datetime.now(UTC).isoformat(),
        }
        write_summary(work, summary)
    log.info("done: %s", summary)
    return summary
