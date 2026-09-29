import pytest
from matrix import rotate, spiral_order


def test_spiral_square():
    assert spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [1, 2, 3, 6, 9, 8, 7, 4, 5]


def test_spiral_rectangles():
    assert spiral_order([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]) == [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]
    assert spiral_order([[1, 2], [3, 4], [5, 6]]) == [1, 2, 4, 6, 5, 3]


def test_spiral_single_row_col():
    assert spiral_order([[1, 2, 3]]) == [1, 2, 3]
    assert spiral_order([[1], [2], [3]]) == [1, 2, 3]
    assert spiral_order([]) == []


def test_spiral_ragged():
    with pytest.raises(ValueError):
        spiral_order([[1, 2, 3], [4, 5]])


def test_rotate_square():
    assert rotate([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [[7, 4, 1], [8, 5, 2], [9, 6, 3]]


def test_rotate_non_square():
    assert rotate([[1, 2, 3], [4, 5, 6]]) == [[4, 1], [5, 2], [6, 3]]


def test_rotate_does_not_mutate_and_four_turns():
    m = [[1, 2], [3, 4], [5, 6]]
    r = m
    for _ in range(4):
        r = rotate(r)
    assert r == m == [[1, 2], [3, 4], [5, 6]]
