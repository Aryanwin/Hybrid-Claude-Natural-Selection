import re
from itertools import groupby


def encode(s: str) -> str:
    if any(c.isdigit() for c in s):
        raise ValueError("digits can't be encoded")
    return "".join(f"{c}{len(list(g))}" for c, g in groupby(s))


def decode(s: str) -> str:
    parts = re.findall(r"(\D)(\d+)", s)
    if "".join(c + n for c, n in parts) != s or any(int(n) == 0 or n[0] == "0" for _, n in parts):
        raise ValueError(f"malformed: {s!r}")
    return "".join(c * int(n) for c, n in parts)
