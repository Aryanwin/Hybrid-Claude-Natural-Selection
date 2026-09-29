import heapq


def topo_sort(deps):
    nodes = set(deps) | {d for ds in deps.values() for d in ds}
    indeg = {n: 0 for n in nodes}
    users = {n: [] for n in nodes}
    for n, ds in deps.items():
        for d in set(ds):
            indeg[n] += 1
            users[d].append(n)
    ready = [n for n in nodes if indeg[n] == 0]
    heapq.heapify(ready)
    out = []
    while ready:
        n = heapq.heappop(ready)
        out.append(n)
        for u in users[n]:
            indeg[u] -= 1
            if indeg[u] == 0:
                heapq.heappush(ready, u)
    if len(out) != len(nodes):
        raise ValueError("cycle detected")
    return out
