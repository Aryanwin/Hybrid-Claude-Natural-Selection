def spiral_order(m):
    if not m:
        return []
    if len({len(r) for r in m}) != 1:
        raise ValueError("ragged matrix")
    out, top, bottom, left, right = [], 0, len(m) - 1, 0, len(m[0]) - 1
    while top <= bottom and left <= right:
        out += [m[top][c] for c in range(left, right + 1)]
        out += [m[r][right] for r in range(top + 1, bottom + 1)]
        if top < bottom:
            out += [m[bottom][c] for c in range(right - 1, left - 1, -1)]
        if left < right:
            out += [m[r][left] for r in range(bottom - 1, top, -1)]
        top, bottom, left, right = top + 1, bottom - 1, left + 1, right - 1
    return out


def rotate(m):
    return [list(row) for row in zip(*m[::-1])]
