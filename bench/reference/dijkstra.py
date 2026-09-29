import heapq


def _run(graph, source):
    if any(w < 0 for edges in graph.values() for _, w in edges):
        raise ValueError("negative weight")
    dist, prev, heap = {source: 0}, {}, [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in graph.get(u, []):
            if d + w < dist.get(v, float("inf")):
                dist[v], prev[v] = d + w, u
                heapq.heappush(heap, (d + w, v))
    return dist, prev


def shortest_paths(graph, source):
    return _run(graph, source)[0]


def shortest_path(graph, source, target):
    dist, prev = _run(graph, source)
    if target not in dist:
        return []
    path = [target]
    while path[-1] != source:
        path.append(prev[path[-1]])
    return path[::-1]
