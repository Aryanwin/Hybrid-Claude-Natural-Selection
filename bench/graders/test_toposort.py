import pytest
from toposort import topo_sort


def test_empty():
    assert topo_sort({}) == []


def test_chain():
    assert topo_sort({"c": ["b"], "b": ["a"], "a": []}) == ["a", "b", "c"]


def test_diamond():
    assert topo_sort({"A": ["B", "C"], "B": ["D"], "C": ["D"]}) == ["D", "B", "C", "A"]


def test_nodes_only_in_lists():
    assert topo_sort({"app": ["lib", "log"]}) == ["lib", "log", "app"]


def test_alphabetical_ties():
    assert topo_sort({"z": [], "m": [], "a": [], "b": ["z"]}) == ["a", "m", "z", "b"]


def test_cycle():
    with pytest.raises(ValueError):
        topo_sort({"a": ["b"], "b": ["c"], "c": ["a"]})


def test_self_cycle():
    with pytest.raises(ValueError):
        topo_sort({"a": ["a"]})


def test_every_dependency_first():
    deps = {f"n{i}": [f"n{j}" for j in range(i) if (i * j) % 3 == 1] for i in range(40)}
    order = topo_sort(deps)
    pos = {n: k for k, n in enumerate(order)}
    assert len(order) == 40 and all(pos[d] < pos[n] for n, ds in deps.items() for d in ds)
