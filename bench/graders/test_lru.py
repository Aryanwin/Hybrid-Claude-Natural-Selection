import pytest
from lru import LRUCache


def test_get_miss():
    assert LRUCache(2).get(1) == -1


def test_put_get():
    c = LRUCache(2)
    c.put(1, "a")
    assert c.get(1) == "a"


def test_evicts_least_recent():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.put(3, 3)
    assert (c.get(1), c.get(2), c.get(3)) == (-1, 2, 3)


def test_get_counts_as_use():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.get(1)
    c.put(3, 3)
    assert (c.get(1), c.get(2)) == (1, -1)


def test_update_counts_as_use_and_keeps_size():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.put(1, 10)
    c.put(3, 3)
    assert (c.get(1), c.get(2), c.get(3)) == (10, -1, 3)


def test_capacity_one():
    c = LRUCache(1)
    c.put("x", 1)
    c.put("y", 2)
    assert (c.get("x"), c.get("y")) == (-1, 2)


def test_bad_capacity():
    for bad in (0, -1):
        with pytest.raises(ValueError):
            LRUCache(bad)


def test_many_operations_fast():
    c = LRUCache(1000)
    for i in range(100_000):
        c.put(i, i)
        c.get(i - 500)
    assert c.get(99_999) == 99_999 and c.get(0) == -1
