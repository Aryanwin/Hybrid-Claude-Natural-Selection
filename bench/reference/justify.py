def justify(words, width):
    if any(len(w) > width for w in words):
        raise ValueError("word longer than width")
    lines, cur = [], []
    for w in words:
        if cur and len(" ".join(cur + [w])) > width:
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    out = []
    for i, line in enumerate(lines):
        if i == len(lines) - 1 or len(line) == 1:
            out.append(" ".join(line).ljust(width))
            continue
        gaps, spaces = len(line) - 1, width - sum(map(len, line))
        q, r = divmod(spaces, gaps)
        out.append("".join(w + (" " * (q + (j < r)) if j < gaps else "") for j, w in enumerate(line)))
    return out
