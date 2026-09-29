def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def closest(word, candidates):
    best = None
    for c in candidates:
        d = edit_distance(word, c)
        if best is None or d < best[0]:
            best = (d, c)
    return best[1] if best else None
