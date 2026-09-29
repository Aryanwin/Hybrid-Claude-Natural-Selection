def knapsack(items, capacity):
    if capacity < 0 or any(w < 0 for _, w, _ in items):
        raise ValueError("negative capacity or weight")
    best = [[0] * (capacity + 1) for _ in range(len(items) + 1)]
    for i, (_, w, v) in enumerate(items, 1):
        for c in range(capacity + 1):
            best[i][c] = best[i - 1][c]
            if w <= c:
                best[i][c] = max(best[i][c], best[i - 1][c - w] + v)
    chosen, c = [], capacity
    for i in range(len(items), 0, -1):
        if best[i][c] != best[i - 1][c]:
            chosen.append(items[i - 1][0])
            c -= items[i - 1][1]
    return best[-1][capacity], chosen[::-1]
