"""
The benchmark tasks. Every approach gets exactly the `spec` text and a stub `<module>.py`; nobody sees the
grader tests in bench/graders/, which are checked against bench/reference/ (python3 bench/run_bench.py --check).
"""

TASKS = [
    ("lru", "algorithm",
     "Implement class LRUCache(capacity: int). get(key) returns the value or -1 if missing; put(key, value) "
     "inserts or updates. When the size exceeds capacity, evict the least recently used key; both a successful "
     "get and a put count as a use. get and put must be O(1). capacity < 1 raises ValueError."),
    ("dijkstra", "algorithm",
     "Implement shortest_paths(graph, source) where graph is dict[str, list[tuple[str, float]]] (directed edges "
     "node -> (neighbor, weight)). Return a dict node -> shortest distance for every node reachable from source "
     "(source maps to 0). Unreachable nodes are omitted; nodes that only appear as neighbors are included when "
     "reachable. Any negative weight in the graph raises ValueError. If source is not a key of graph, return "
     "{source: 0}. Also implement shortest_path(graph, source, target) -> list[str] of nodes from source to "
     "target inclusive, [] if unreachable, [source] if target == source."),
    ("roman", "parsing",
     "Implement to_roman(n: int) -> str for 1..3999 in canonical subtractive form (e.g. 1994 -> 'MCMXCIV'), "
     "raising ValueError outside that range. Implement from_roman(s: str) -> int that accepts only canonical "
     "uppercase numerals and raises ValueError for anything else (e.g. 'IIII', 'IC', 'VV', '', 'iv', 'MMMM')."),
    ("intervals", "algorithm",
     "Implement merge_intervals(intervals: list[list[int]]) -> list[list[int]]: return the intervals sorted by "
     "start with overlapping or touching ones merged ([1,2] and [2,3] -> [1,3]). An interval with start > end "
     "raises ValueError. Empty input returns []. Do not mutate the input."),
    ("toposort", "algorithm",
     "Implement topo_sort(deps: dict[str, list[str]]) -> list[str]. deps maps a node to the nodes it depends on. "
     "Return every node (including nodes that only appear inside the lists), each placed after all of its "
     "dependencies. Whenever several nodes are ready, take the alphabetically smallest first, so the output is "
     "deterministic. A cycle (including a node depending on itself) raises ValueError."),
    ("levenshtein", "algorithm",
     "Implement edit_distance(a: str, b: str) -> int (Levenshtein: insert, delete, substitute each cost 1; must "
     "handle 400-character strings quickly). Implement closest(word, candidates) returning the candidate with the "
     "smallest edit distance to word, ties broken by earliest position in the list, or None for an empty list."),
    ("calc", "parsing",
     "Implement evaluate(expr: str) -> float without using eval(). Support + - * / ^, parentheses, unary minus, "
     "decimal numbers (including '.25') and arbitrary whitespace. ^ is right-associative and binds tighter than "
     "unary minus ('-2^2' == -4, '2^3^2' == 512); * and / bind tighter than + and -, all left-associative. "
     "Division by zero raises ZeroDivisionError. Malformed input ('', '2 +', '(1', '1 2', '2 $ 3', '* 3') "
     "raises ValueError."),
    ("knapsack", "algorithm",
     "Implement knapsack(items: list[tuple[str, int, int]], capacity: int) -> tuple[int, list[str]] for 0/1 "
     "knapsack. items are (name, weight, value). Return the best total value and the names of the chosen items "
     "in input order; each item is used at most once and total weight must not exceed capacity. Negative "
     "capacity or a negative weight raises ValueError. Empty items returns (0, [])."),
    ("autocomplete", "data structure",
     "Implement class Autocomplete. add(word, weight=1) adds weight to the word's running total (words are "
     "case-insensitive and stored lowercase). suggest(prefix, k=5) returns up to k stored words starting with "
     "prefix (case-insensitive), sorted by total weight descending, then alphabetically. remove(word) deletes "
     "the word and returns True, or returns False if it wasn't stored."),
    ("duration", "parsing",
     "Implement parse_duration(s: str) -> int seconds for strings like '1h30m', '2d 4h', '45s', '1h 2m 3s', "
     "'90m'. Units are d, h, m, s (case-insensitive), with optional whitespace between parts; each unit may "
     "appear at most once and only in the order d, h, m, s. Anything else ('', '5', '1x', '1m1h', '1h1h', 'h') "
     "raises ValueError. Implement format_duration(seconds: int) -> str giving the canonical form such as "
     "'1d2h3m4s' with zero parts omitted, '0s' for 0, and ValueError for negative input."),
    ("justify", "text",
     "Implement justify(words: list[str], width: int) -> list[str] (full text justification). Pack words "
     "greedily into lines. Every line except the last has exactly width characters, with the extra spaces "
     "spread as evenly as possible between words and the leftmost gaps getting any extra. A line holding a "
     "single word is left-justified and padded with spaces to width. The last line is left-justified with single "
     "spaces and padded to width. A word longer than width raises ValueError. An empty list returns []."),
    ("rle", "text",
     "Implement encode(s: str) -> str: run-length encoding written as each character followed by its run length, "
     "e.g. 'aaabcc' -> 'a3b1c2' and '' -> ''. Input containing digits raises ValueError. Implement decode(s) as "
     "the exact inverse ('a3b1c2' -> 'aaabcc'; counts may have several digits, 'x12' -> twelve x's). Malformed "
     "input such as '3a', 'a', 'a0', 'ab2' or a count with a leading zero raises ValueError."),
    ("matrix", "algorithm",
     "Implement spiral_order(m: list[list[int]]) -> list[int], the elements in clockwise spiral order starting at "
     "the top-left; [] returns []; rows of different lengths raise ValueError. Implement rotate(m) returning a "
     "new matrix rotated 90 degrees clockwise (the input must not be mutated); it must work for non-square "
     "matrices too."),
    ("sudoku", "algorithm",
     "Implement solve(grid: list[list[int]]) for a 9x9 sudoku with 0 for empty cells. Return a new, fully solved "
     "grid (do not mutate the input), or None if the puzzle has no solution. A wrong shape, values outside 0-9, "
     "or givens that already conflict raise ValueError. Typical newspaper puzzles must solve in a few seconds."),
]
