import pytest
from calc import evaluate


def test_basic():
    assert evaluate("1 + 2") == 3
    assert evaluate("7 - 10") == -3
    assert evaluate("3 * 4 / 2") == 6


def test_precedence_and_parens():
    assert evaluate("2 + 3 * 4") == 14
    assert evaluate("(2 + 3) * 4") == 20
    assert evaluate("10 - 4 - 3") == 3
    assert evaluate("100 / 10 / 5") == 2


def test_power():
    assert evaluate("2 ^ 3 ^ 2") == 512
    assert evaluate("-2 ^ 2") == -4
    assert evaluate("(-2) ^ 2") == 4


def test_unary_and_decimals():
    assert evaluate("-(3 + 4)") == -7
    assert evaluate("2 * -3") == -6
    assert evaluate("1.5 + .25") == pytest.approx(1.75)
    assert evaluate("  4   /8 ") == pytest.approx(0.5)


def test_nested():
    assert evaluate("((1 + 2) * (3 + 4)) ^ 2 / 21") == pytest.approx(21)


def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        evaluate("1 / (2 - 2)")


def test_malformed():
    for bad in ("", "2 +", "(1", "1 2", "2 $ 3", ")(", "* 3"):
        with pytest.raises(ValueError):
            evaluate(bad)
