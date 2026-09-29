def solve(grid):
    if len(grid) != 9 or any(len(r) != 9 for r in grid):
        raise ValueError("grid must be 9x9")
    g = [list(r) for r in grid]
    if any(not isinstance(v, int) or not 0 <= v <= 9 for r in g for v in r):
        raise ValueError("values must be 0-9")

    def ok(r, c, v):
        br, bc = r // 3 * 3, c // 3 * 3
        return all(g[r][j] != v for j in range(9) if j != c) and all(g[i][c] != v for i in range(9) if i != r) \
            and all(g[i][j] != v for i in range(br, br + 3) for j in range(bc, bc + 3) if (i, j) != (r, c))

    if any(g[r][c] and not ok(r, c, g[r][c]) for r in range(9) for c in range(9)):
        raise ValueError("conflicting givens")
    empty = [(r, c) for r in range(9) for c in range(9) if not g[r][c]]

    def bt(k):
        if k == len(empty):
            return True
        r, c = empty[k]
        for v in range(1, 10):
            if ok(r, c, v):
                g[r][c] = v
                if bt(k + 1):
                    return True
        g[r][c] = 0
        return False

    return g if bt(0) else None
