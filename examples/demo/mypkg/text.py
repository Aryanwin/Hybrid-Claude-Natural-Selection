"""Small text helpers."""


def normalize_whitespace(s: str) -> str:
    """Collapse runs of whitespace into single spaces and strip the ends."""
    return " ".join(s.split())
