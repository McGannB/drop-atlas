"""Clean Discogs 'released' values like '2012-03-00', '2012' or '?'."""

from __future__ import annotations

import re
from datetime import date

_PATTERN = re.compile(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?$")
MIN_YEAR = 1860


def clean_released(raw: str | None, max_year: int | None = None) -> tuple[date | None, str | None]:
    """Return (first day of the period, precision) for a Discogs release date.

    precision is 'day', 'month' or 'year'. Unusable values return (None, None).
    """
    if raw is None:
        return None, None
    match = _PATTERN.match(raw.strip())
    if not match:
        return None, None
    year = int(match.group(1))
    month = int(match.group(2) or 0)
    day = int(match.group(3) or 0)
    max_year = max_year or date.today().year + 1
    if not MIN_YEAR <= year <= max_year:
        return None, None
    if not 1 <= month <= 12:
        return date(year, 1, 1), "year"
    if day == 0:
        return date(year, month, 1), "month"
    try:
        return date(year, month, day), "day"
    except ValueError:  # a day that doesn't exist, like 2012-02-30
        return date(year, month, 1), "month"
