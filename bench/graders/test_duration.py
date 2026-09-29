import pytest
from duration import format_duration, parse_duration


def test_parse():
    assert parse_duration("1h30m") == 5400
    assert parse_duration("2d 4h") == 187200
    assert parse_duration("45s") == 45
    assert parse_duration("1h 2m 3s") == 3723
    assert parse_duration("90m") == 5400


def test_parse_case_and_space():
    assert parse_duration("1D 1S") == 86401
    assert parse_duration("  3m  ") == 180


def test_parse_zero_parts():
    assert parse_duration("0s") == 0
    assert parse_duration("1d0h5s") == 86405


def test_parse_invalid():
    for bad in ("", "5", "1x", "1m1h", "1h1h", "h", "1.5h", "-1h", "1 h x"):
        with pytest.raises(ValueError):
            parse_duration(bad)


def test_format():
    assert format_duration(5400) == "1h30m"
    assert format_duration(187200) == "2d4h"
    assert format_duration(3723) == "1h2m3s"
    assert format_duration(86401) == "1d1s"
    assert format_duration(0) == "0s"


def test_round_trip():
    for n in (1, 59, 60, 3599, 3600, 90061, 10**7):
        assert parse_duration(format_duration(n)) == n


def test_format_negative():
    with pytest.raises(ValueError):
        format_duration(-1)
