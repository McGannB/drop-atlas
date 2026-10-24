"""Write rows to Parquet in batches so memory stays flat on any size of input."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


class ChunkedParquetWriter:
    """Buffer rows, write them in row groups, and start a new file every rows_per_file rows."""

    def __init__(self, out_dir: Path, schema: pa.Schema, rows_per_file=1_000_000, batch_size=25_000):
        self.out_dir = Path(out_dir)
        self.schema = schema
        self.rows_per_file = rows_per_file
        self.batch_size = batch_size
        self.files: list[Path] = []
        self.rows = 0
        self._buffer: list[dict] = []
        self._writer: pq.ParquetWriter | None = None
        self._file_rows = 0

    def write(self, row: dict) -> None:
        self._buffer.append(row)
        if len(self._buffer) >= self.batch_size:
            self._flush()

    def _flush(self) -> None:
        if not self._buffer:
            return
        if self._writer is None:
            path = self.out_dir / f"part-{len(self.files):05d}.parquet"
            self._writer = pq.ParquetWriter(path, self.schema, compression="zstd")
            self.files.append(path)
        self._writer.write_table(pa.Table.from_pylist(self._buffer, schema=self.schema))
        self._file_rows += len(self._buffer)
        self.rows += len(self._buffer)
        self._buffer = []
        if self._file_rows >= self.rows_per_file:
            self._writer.close()
            self._writer = None
            self._file_rows = 0

    def close(self) -> None:
        self._flush()
        if self._writer is not None:
            self._writer.close()
            self._writer = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class PartialDir:
    """Write into '<out>.partial' and swap it into place only when everything succeeded.

    A crash leaves the old output untouched, so a rerun always starts clean.
    """

    def __init__(self, out_dir: str | Path):
        self.final = Path(out_dir)
        self.path = self.final.with_name(self.final.name + ".partial")

    def __enter__(self) -> Path:
        if self.path.exists():
            shutil.rmtree(self.path)
        self.path.mkdir(parents=True)
        return self.path

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            return False  # leave .partial behind for debugging; the old output is untouched
        if self.final.exists():
            shutil.rmtree(self.final)
        self.path.rename(self.final)
        return False


def write_summary(folder: Path, summary: dict) -> None:
    # Files starting with "_" are skipped by Spark when it reads the folder as Parquet.
    (folder / "_run_summary.json").write_text(json.dumps(summary, indent=2, default=str))
