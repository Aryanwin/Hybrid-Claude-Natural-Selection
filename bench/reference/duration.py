import re

UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}
PATTERN = re.compile(r"^\s*(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?\s*$", re.I)


def parse_duration(s: str) -> int:
    m = PATTERN.match(s or "")
    if not m or not any(m.groups()):
        raise ValueError(f"bad duration: {s!r}")
    return sum(int(g) * u for g, u in zip(m.groups(), UNITS.values()) if g)


def format_duration(seconds: int) -> str:
    if seconds < 0:
        raise ValueError("negative")
    out = ""
    for unit, size in UNITS.items():
        n, seconds = divmod(seconds, size)
        if n:
            out += f"{n}{unit}"
    return out or "0s"
