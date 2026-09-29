import pytest
from roman import from_roman, to_roman

CASES = {1: "I", 4: "IV", 9: "IX", 14: "XIV", 40: "XL", 58: "LVIII", 90: "XC", 400: "CD",
         944: "CMXLIV", 1994: "MCMXCIV", 2024: "MMXXIV", 3999: "MMMCMXCIX"}


def test_to_roman():
    for n, s in CASES.items():
        assert to_roman(n) == s


def test_from_roman():
    for n, s in CASES.items():
        assert from_roman(s) == n


def test_round_trip_all():
    assert all(from_roman(to_roman(n)) == n for n in range(1, 4000))


def test_to_roman_range():
    for bad in (0, -5, 4000):
        with pytest.raises(ValueError):
            to_roman(bad)


def test_from_roman_rejects_non_canonical():
    for bad in ("IIII", "IC", "VV", "", "iv", "MMMM", "IIV", "XM", "ABC", "VX"):
        with pytest.raises(ValueError):
            from_roman(bad)
