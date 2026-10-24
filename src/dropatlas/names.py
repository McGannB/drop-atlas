"""One tested way to turn artist names into match keys, used on both sides of the join."""

from __future__ import annotations

import re
import unicodedata

_DISAMBIGUATION = re.compile(r"\s*\(\d+\)$")  # Discogs adds "(2)" to tell namesakes apart
_SEPARATORS = re.compile(
    r"\s+(?:&|and|x|vs\.?|feat\.?|ft\.?|featuring|with)\s+|\s*,\s*",
    re.IGNORECASE,
)


def normalize_name(name: str) -> str:
    """Lowercase, strip accents and punctuation, drop a leading 'the' and Discogs '(2)'."""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().strip()
    text = _DISAMBIGUATION.sub("", text)
    text = text.replace("&", " and ")
    text = re.sub(r"^the\s+", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_credit(name: str) -> list[str]:
    """Split 'Seven Lions & Illenium feat. X' into normalized parts, in order, no repeats."""
    parts: list[str] = []
    for piece in _SEPARATORS.split(name):
        key = normalize_name(piece)
        if key and key not in parts:
            parts.append(key)
    return parts
