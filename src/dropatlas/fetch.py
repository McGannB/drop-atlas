"""Download big files safely: resume after a dropped connection, verify the checksum."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)

USER_AGENT = "drop-atlas/0.1 (+https://github.com/mcgannb/drop-atlas)"
DISCOGS_URL = "https://data.discogs.com/?download=data%2F{year}%2F{name}"


class ChecksumError(RuntimeError):
    pass


def discogs_name(month: str, kind: str) -> str:
    """month '2026-10', kind 'releases' -> 'discogs_20261001_releases.xml.gz'."""
    year, mm = month.split("-")
    suffix = "CHECKSUM.txt" if kind == "CHECKSUM" else f"{kind}.xml.gz"
    return f"discogs_{year}{mm}01_{suffix}"


def discogs_url(month: str, kind: str) -> str:
    return DISCOGS_URL.format(year=month.split("-")[0], name=discogs_name(month, kind))


def parse_checksums(text: str) -> dict[str, str]:
    """'<sha256> <filename>' lines -> {filename: sha256}."""
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            out[parts[1].lstrip("*")] = parts[0].lower()
    return out


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def download(
    url: str,
    dest: str | Path,
    expected_sha256: str | None = None,
    attempts: int = 6,
    session: requests.Session | None = None,
    sleep=time.sleep,
) -> Path:
    """Stream url to dest. Resumes from dest.part with a Range request after a failure."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (expected_sha256 is None or sha256_of(dest) == expected_sha256):
        log.info("already have %s", dest.name)
        return dest
    part = dest.with_name(dest.name + ".part")
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)

    for attempt in range(1, attempts + 1):
        have = part.stat().st_size if part.exists() else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with session.get(url, headers=headers, stream=True, timeout=60) as resp:
                if resp.status_code == 416:  # nothing left to fetch: the .part is complete
                    break
                resp.raise_for_status()
                if have and resp.status_code != 206:  # server ignored Range: start over
                    have = 0
                mode = "ab" if have else "wb"
                next_log = have + (500 << 20)
                with open(part, mode) as fh:
                    for block in resp.iter_content(chunk_size=1 << 20):
                        fh.write(block)
                        have += len(block)
                        if have >= next_log:
                            log.info("%s: %.1f GB", dest.name, have / 1e9)
                            next_log += 500 << 20
            break
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as exc:
            wait = min(60, 2**attempt)
            log.warning("attempt %d failed (%s); resuming in %ds", attempt, exc, wait)
            sleep(wait)
    else:
        raise RuntimeError(f"gave up on {url} after {attempts} attempts")

    if expected_sha256:
        actual = sha256_of(part)
        if actual != expected_sha256:
            part.unlink()
            raise ChecksumError(f"{dest.name}: expected {expected_sha256}, got {actual}")
    part.replace(dest)
    return dest
