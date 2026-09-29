import pytest
from knapsack import knapsack

ITEMS = [("a", 2, 3), ("b", 3, 4), ("c", 4, 5), ("d", 5, 6)]


def test_classic():
    assert knapsack(ITEMS, 5) == (7, ["a", "b"])


def test_best_value_and_weight_limit():
    value, names = knapsack(ITEMS, 9)
    chosen = [i for i in ITEMS if i[0] in names]
    assert value == 12 and sum(i[1] for i in chosen) <= 9 and sum(i[2] for i in chosen) == 12


def test_greedy_by_ratio_is_wrong_here():
    assert knapsack([("x", 6, 30), ("y", 3, 14), ("z", 4, 16), ("w", 2, 9)], 10)[0] == 46


def test_names_in_input_order():
    assert knapsack([("big", 5, 10), ("small", 1, 1)], 6) == (11, ["big", "small"])


def test_nothing_fits_and_empty():
    assert knapsack(ITEMS, 1) == (0, [])
    assert knapsack(ITEMS, 0) == (0, [])
    assert knapsack([], 5) == (0, [])


def test_zero_weight_item_taken():
    assert knapsack([("free", 0, 5), ("a", 3, 3)], 2) == (5, ["free"])


def test_errors():
    with pytest.raises(ValueError):
        knapsack(ITEMS, -1)
    with pytest.raises(ValueError):
        knapsack([("a", -2, 3)], 5)
