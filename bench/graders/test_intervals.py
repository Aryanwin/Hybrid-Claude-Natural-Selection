import pytest
from intervals import merge_intervals


def test_empty():
    assert merge_intervals([]) == []


def test_disjoint_sorted():
    assert merge_intervals([[5, 7], [1, 3]]) == [[1, 3], [5, 7]]


def test_overlap_and_touching():
    assert merge_intervals([[1, 3], [2, 4], [4, 5], [7, 8]]) == [[1, 5], [7, 8]]


def test_contained():
    assert merge_intervals([[1, 10], [2, 3], [4, 5]]) == [[1, 10]]


def test_point_intervals():
    assert merge_intervals([[3, 3], [3, 3], [1, 1]]) == [[1, 1], [3, 3]]


def test_negative_numbers():
    assert merge_intervals([[-5, -1], [-2, 2]]) == [[-5, 2]]


def test_bad_interval():
    with pytest.raises(ValueError):
        merge_intervals([[1, 2], [4, 3]])


def test_input_not_mutated():
    data = [[3, 4], [1, 2], [2, 3]]
    merge_intervals(data)
    assert data == [[3, 4], [1, 2], [2, 3]]
