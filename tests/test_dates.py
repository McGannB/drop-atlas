from datetime import date

import pytest

from dropatlas.dates import clean_released


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2012-03-05", (date(2012, 3, 5), "day")),
        ("2012-03-00", (date(2012, 3, 1), "month")),
        ("2012-03", (date(2012, 3, 1), "month")),
        ("2012-00-00", (date(2012, 1, 1), "year")),
        ("2012", (date(2012, 1, 1), "year")),
        ("2012-13-01", (date(2012, 1, 1), "year")),
        ("2012-02-30", (date(2012, 2, 1), "month")),
        (" 2019-03-15 ", (date(2019, 3, 15), "day")),
        ("?", (None, None)),
        ("", (None, None)),
        (None, (None, None)),
        ("1700", (None, None)),
        ("Unknown", (None, None)),
    ],
)
def test_clean_released(raw, expected):
    assert clean_released(raw, max_year=2027) == expected
