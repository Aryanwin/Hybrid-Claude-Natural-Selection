import pytest
from rle import decode, encode


def test_encode():
    assert encode("aaabcc") == "a3b1c2"
    assert encode("") == ""
    assert encode("abc") == "a1b1c1"
    assert encode("x" * 12) == "x12"


def test_encode_spaces_and_symbols():
    assert encode("  !!") == " 2!2"


def test_encode_digits_rejected():
    with pytest.raises(ValueError):
        encode("a1")


def test_decode():
    assert decode("a3b1c2") == "aaabcc"
    assert decode("") == ""
    assert decode("x12") == "x" * 12


def test_round_trip():
    for s in ("hello world", "aaaaaaaaaaaaaaaaaaaaaaab", "mississippi", "?"):
        assert decode(encode(s)) == s


def test_decode_malformed():
    for bad in ("3a", "a", "a0", "ab2", "a01", "a3b"):
        with pytest.raises(ValueError):
            decode(bad)
