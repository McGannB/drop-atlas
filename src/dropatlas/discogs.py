"""Turn Discogs XML elements into plain dicts, one row per record."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .dates import clean_released
from .names import normalize_name


def _text(elem: ET.Element, path: str) -> str | None:
    found = elem.find(path)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def _int(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


def _texts(elem: ET.Element, path: str) -> list[str]:
    return [e.text.strip() for e in elem.findall(path) if e.text and e.text.strip()]


def _ids(elem: ET.Element, path: str) -> list[int]:
    return [int(e.get("id")) for e in elem.findall(path) if e.get("id")]


def _credits(parent: ET.Element | None) -> list[dict]:
    if parent is None:
        return []
    return [
        {
            "artist_id": _int(_text(a, "id")),
            "name": _text(a, "name"),
            "anv": _text(a, "anv"),
            "join_phrase": _text(a, "join"),
            "role": _text(a, "role"),
        }
        for a in parent.findall("artist")
    ]


def parse_release(elem: ET.Element) -> dict:
    released_raw = _text(elem, "released")
    released_date, precision = clean_released(released_raw)
    master = elem.find("master_id")
    return {
        "release_id": int(elem.get("id")),
        "status": elem.get("status"),
        "title": _text(elem, "title"),
        "country": _text(elem, "country"),
        "released_raw": released_raw,
        "released_date": released_date,
        "released_precision": precision,
        "master_id": _int(master.text.strip()) if master is not None and master.text else None,
        "is_main_release": master is not None and master.get("is_main_release") == "true",
        "data_quality": _text(elem, "data_quality"),
        # Only the release-level credits. Track-level <artists> live under <tracklist>.
        "artists": _credits(elem.find("artists")),
        "extra_artists": _credits(elem.find("extraartists")),
        "labels": [
            {"label_id": _int(lab.get("id")), "name": lab.get("name"), "catno": lab.get("catno")}
            for lab in elem.findall("labels/label")
        ],
        "genres": _texts(elem, "genres/genre"),
        "styles": _texts(elem, "styles/style"),
        "formats": [
            {
                "name": fmt.get("name"),
                "qty": fmt.get("qty"),
                "descriptions": _texts(fmt, "descriptions/description"),
            }
            for fmt in elem.findall("formats/format")
        ],
        "track_count": len(elem.findall("tracklist/track")),
    }


def parse_artist(elem: ET.Element) -> dict:
    name = _text(elem, "name")
    return {
        "artist_id": int(_text(elem, "id")),
        "name": name,
        "name_norm": normalize_name(name) if name else None,
        "realname": _text(elem, "realname"),
        "profile": _text(elem, "profile"),
        "data_quality": _text(elem, "data_quality"),
        "urls": _texts(elem, "urls/url"),
        "name_variations": _texts(elem, "namevariations/name"),
        "alias_ids": _ids(elem, "aliases/name"),
        "group_ids": _ids(elem, "groups/name"),
        "member_ids": _ids(elem, "members/name"),
    }


def parse_label(elem: ET.Element) -> dict:
    parent = elem.find("parentLabel")
    return {
        "label_id": int(_text(elem, "id")),
        "name": _text(elem, "name"),
        "profile": _text(elem, "profile"),
        "data_quality": _text(elem, "data_quality"),
        "parent_label_id": _int(parent.get("id")) if parent is not None else None,
        "parent_label_name": parent.text.strip() if parent is not None and parent.text else None,
        "sublabel_ids": _ids(elem, "sublabels/label"),
        "urls": _texts(elem, "urls/url"),
    }
