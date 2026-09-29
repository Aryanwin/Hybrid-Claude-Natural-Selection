import re

TOKEN = re.compile(r"\s*(?:(\d+\.?\d*|\.\d+)|(.))")


def evaluate(expr: str) -> float:
    toks = []
    for num, op in TOKEN.findall(expr):
        if num:
            toks.append(float(num))
        elif op.strip():
            if op not in "+-*/^()":
                raise ValueError(f"bad character {op!r}")
            toks.append(op)
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def take():
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def expr_():
        v = term()
        while peek() in ("+", "-"):
            v = v + term() if take() == "+" else v - term()
        return v

    def term():
        v = unary()
        while peek() in ("*", "/"):
            if take() == "*":
                v *= unary()
            else:
                d = unary()
                if d == 0:
                    raise ZeroDivisionError("division by zero")
                v /= d
        return v

    def unary():
        if peek() == "-":
            take()
            return -unary()
        return power()

    def power():
        base = atom()
        if peek() == "^":
            take()
            return base ** unary()
        return base

    def atom():
        t = peek()
        if isinstance(t, float):
            return take()
        if t == "(":
            take()
            v = expr_()
            if peek() != ")":
                raise ValueError("missing )")
            take()
            return v
        raise ValueError(f"unexpected {t!r}")

    v = expr_()
    if pos != len(toks):
        raise ValueError("trailing input")
    return v
