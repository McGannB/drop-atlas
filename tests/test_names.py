import pytest

from dropatlas.names import normalize_name, split_credit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Seven Lions", "seven lions"),
        ("  SAID   THE SKY ", "said the sky"),
        ("Röyksopp", "royksopp"),
        ("Above & Beyond", "above and beyond"),
        ("The Chainsmokers", "chainsmokers"),
        ("Seven Lions (2)", "seven lions"),
        ("Ke$ha", "ke ha"),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_split_credit_handles_common_separators():
    assert split_credit("Seven Lions & Illenium feat. Said The Sky") == [
        "seven lions",
        "illenium",
        "said the sky",
    ]
    assert split_credit("Virtual Riot x Seven Lions, Illenium") == [
        "virtual riot",
        "seven lions",
        "illenium",
    ]


def test_split_credit_breaks_band_names_so_full_name_must_be_tried_first():
    # This is why matching tries the whole name before the parts.
    assert split_credit("Above & Beyond") == ["above", "beyond"]
