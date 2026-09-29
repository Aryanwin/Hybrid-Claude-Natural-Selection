import pytest
from dijkstra import shortest_path, shortest_paths

G = {"A": [("B", 1), ("C", 4)], "B": [("C", 2), ("D", 7)], "C": [("D", 1)], "E": [("A", 1)]}


def test_distances():
    assert shortest_paths(G, "A") == {"A": 0, "B": 1, "C": 3, "D": 4}


def test_unreachable_omitted():
    assert "E" not in shortest_paths(G, "A")


def test_neighbor_only_node_included():
    assert shortest_paths({"A": [("Z", 2.5)]}, "A") == {"A": 0, "Z": 2.5}


def test_source_missing():
    assert shortest_paths({"A": []}, "Q") == {"Q": 0}


def test_negative_weight():
    with pytest.raises(ValueError):
        shortest_paths({"A": [("B", -1)]}, "A")


def test_path():
    assert shortest_path(G, "A", "D") == ["A", "B", "C", "D"]


def test_path_unreachable_and_self():
    assert shortest_path(G, "A", "E") == []
    assert shortest_path(G, "A", "A") == ["A"]


def test_cycle_graph():
    g = {"a": [("b", 1)], "b": [("c", 1), ("a", 1)], "c": [("a", 5)]}
    assert shortest_paths(g, "b") == {"b": 0, "a": 1, "c": 1}
