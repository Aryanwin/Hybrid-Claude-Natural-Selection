import copy
import time

import pytest
from sudoku import solve

PUZZLE = [[5, 3, 0, 0, 7, 0, 0, 0, 0], [6, 0, 0, 1, 9, 5, 0, 0, 0], [0, 9, 8, 0, 0, 0, 0, 6, 0],
          [8, 0, 0, 0, 6, 0, 0, 0, 3], [4, 0, 0, 8, 0, 3, 0, 0, 1], [7, 0, 0, 0, 2, 0, 0, 0, 6],
          [0, 6, 0, 0, 0, 0, 2, 8, 0], [0, 0, 0, 4, 1, 9, 0, 0, 5], [0, 0, 0, 0, 8, 0, 0, 7, 9]]
SOLUTION = [[5, 3, 4, 6, 7, 8, 9, 1, 2], [6, 7, 2, 1, 9, 5, 3, 4, 8], [1, 9, 8, 3, 4, 2, 5, 6, 7],
            [8, 5, 9, 7, 6, 1, 4, 2, 3], [4, 2, 6, 8, 5, 3, 7, 9, 1], [7, 1, 3, 9, 2, 4, 8, 5, 6],
            [9, 6, 1, 5, 3, 7, 2, 8, 4], [2, 8, 7, 4, 1, 9, 6, 3, 5], [3, 4, 5, 2, 8, 6, 1, 7, 9]]


def valid(g):
    groups = [r for r in g] + [list(c) for c in zip(*g)] + \
             [[g[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3)] for br in (0, 3, 6) for bc in (0, 3, 6)]
    return all(sorted(x) == list(range(1, 10)) for x in groups)


def test_solves_classic():
    assert solve(PUZZLE) == SOLUTION


def test_input_not_mutated():
    p = copy.deepcopy(PUZZLE)
    solve(p)
    assert p == PUZZLE


def test_harder_puzzle_quickly():
    rows = ["000000907", "000420180", "000705026", "100904000", "050000040",
            "000507009", "920108000", "034059000", "507000000"]
    g = [[int(ch) for ch in r] for r in rows]
    t = time.time()
    out = solve(g)
    assert out and valid(out) and time.time() - t < 10
    assert all(out[r][c] == g[r][c] for r in range(9) for c in range(9) if g[r][c])


def test_unsolvable_returns_none():
    g = [[0] * 9 for _ in range(9)]
    g[0] = [0, 1, 2, 3, 4, 5, 6, 7, 0]
    g[3][0], g[6][0] = 8, 9
    assert solve(g) is None


def test_bad_shape():
    with pytest.raises(ValueError):
        solve([row[:8] for row in PUZZLE])
    with pytest.raises(ValueError):
        solve(PUZZLE[:8])


def test_bad_values():
    g = copy.deepcopy(PUZZLE)
    g[8][8] = 10
    with pytest.raises(ValueError):
        solve(g)


def test_conflicting_givens():
    g = copy.deepcopy(PUZZLE)
    g[0][2] = 5
    with pytest.raises(ValueError):
        solve(g)
