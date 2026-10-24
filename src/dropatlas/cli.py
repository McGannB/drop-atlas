"""Command line entry point: `uv run dropatlas <command> --help`."""

from __future__ import annotations

import argparse
import gzip
import logging
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from . import fetch
from .convert import KINDS, convert_dump
from .xmlstream import iter_records, open_dump

log = logging.getLogger("dropatlas")


def cmd_discogs_fetch(args) -> None:
    dest = Path(args.data) / "discogs"
    checksum_file = fetch.download(
        fetch.discogs_url(args.month, "CHECKSUM"), dest / fetch.discogs_name(args.month, "CHECKSUM")
    )
    sums = fetch.parse_checksums(checksum_file.read_text())
    if not sums:
        sys.exit(f"{checksum_file} has no checksums in it. Open it: the download link may have changed.")
    for kind in args.kinds:
        name = fetch.discogs_name(args.month, kind)
        log.info("downloading %s", name)
        fetch.download(fetch.discogs_url(args.month, kind), dest / name, expected_sha256=sums.get(name))
        log.info("verified %s", name)


def cmd_discogs_convert(args) -> None:
    src = Path(args.data) / "discogs" / fetch.discogs_name(args.month, args.kind)
    out = Path(args.landing) / "discogs" / args.kind / f"snapshot={args.month}-01"
    summary = convert_dump(src, out, args.kind, limit=args.limit)
    print(
        f"{summary['rows_written']:,} rows, {summary['bad_records']} bad, "
        f"{summary['control_bytes_removed']} control bytes removed, {summary['seconds']}s -> {out}"
    )


def cmd_discogs_sample(args) -> None:
    tag = KINDS[args.kind][0]
    with gzip.open(args.out, "wb") as fh:
        fh.write(f"<{args.kind}>\n".encode())
        for n, elem in enumerate(iter_records(open_dump(args.src), tag), start=1):
            fh.write(ET.tostring(elem, encoding="unicode").strip().encode("utf-8") + b"\n")
            if n >= args.n:
                break
        fh.write(f"</{args.kind}>\n".encode())
    print(f"wrote {args.n} {args.kind} to {args.out}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dropatlas")
    p.add_argument("--data", default="data", help="where raw downloads go")
    p.add_argument("--landing", default="landing", help="local mirror of the Databricks volume")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("discogs-fetch", help="download and verify one month of Discogs dumps")
    s.add_argument("--month", required=True, help="YYYY-MM, e.g. 2026-10")
    s.add_argument("--kinds", nargs="+", default=["labels", "artists", "releases"])
    s.set_defaults(func=cmd_discogs_fetch)

    s = sub.add_parser("discogs-convert", help="stream one Discogs dump into Parquet")
    s.add_argument("--month", required=True)
    s.add_argument("--kind", choices=sorted(KINDS), required=True)
    s.add_argument("--limit", type=int, help="stop after N records (for quick test runs)")
    s.set_defaults(func=cmd_discogs_convert)

    s = sub.add_parser("discogs-sample", help="copy the first N records into a small fixture")
    s.add_argument("--src", required=True)
    s.add_argument("--kind", choices=sorted(KINDS), required=True)
    s.add_argument("--n", type=int, default=200)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_discogs_sample)
    return p


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
