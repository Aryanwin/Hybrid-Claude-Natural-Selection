#!/usr/bin/env python3
"""
checkers.py - a game of checkers where a local LLM (Ollama) plays Black against a simulated minimax
opponent (White). Doubles as a health check for the evolve setup:

  - local models: is Ollama up, does each model answer, how often does it pick a legal move, how fast
  - 🟢 tracker:   do the model calls land in ~/.cache/evolve/ledger.jsonl with exact token counts
  - 🔴 tracker:   is the Claude Code Stop hook (token_footer.py) registered and producing its footer

    python3 checkers.py                          one game, best installed model vs the simulated opponent
    python3 checkers.py --model all              one game per installed model
    python3 checkers.py --model qwen2.5-coder:7b --depth 1 --max-plies 60
    python3 checkers.py --selftest               rules tests only (no Ollama needed)
    python3 checkers.py --sim                    watch two simulated opponents (no Ollama needed)

When the games finish, a turn-by-turn visual replay opens in your browser (checkers_viewer.py);
pass --no-view to skip it. Saved games live in checkers_games/.

American checkers rules: Black moves first, men move diagonally forward, captures are mandatory,
multi-jumps must be completed, reaching the far row crowns a king (and ends the move).
Draw after 40 moves by each side without a capture, or at --max-plies.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import evolve_chat as ec  # noqa: E402  (same Ollama client + ledger the MCP server uses)
import checkers_viewer  # noqa: E402

TTY = sys.stdout.isatty()
RED, GREEN, DIM, BOLD, RESET = ("\033[31m", "\033[32m", "\033[2m", "\033[1m", "\033[0m") if TTY else ("",) * 5

# ----------------------------------------------------------------------------- rules

EMPTY = "."
FILES = "abcdefgh"


def new_board() -> list[list[str]]:
    b = [[EMPTY] * 8 for _ in range(8)]
    for r in range(8):
        for c in range(8):
            if (r + c) % 2 == 1:
                if r <= 2:
                    b[r][c] = "b"
                elif r >= 5:
                    b[r][c] = "w"
    return b


def side(p: str) -> str:
    return p.lower() if p != EMPTY else ""


def directions(p: str):
    if p in "BW":
        return [(1, -1), (1, 1), (-1, -1), (-1, 1)]
    return [(1, -1), (1, 1)] if p == "b" else [(-1, -1), (-1, 1)]


def inside(r: int, c: int) -> bool:
    return 0 <= r < 8 and 0 <= c < 8


def crown_row(p: str) -> int:
    return 7 if p == "b" else 0


def _jumps(b, r, c, path):
    p, out = b[r][c], []
    for dr, dc in directions(p):
        mr, mc, lr, lc = r + dr, c + dc, r + 2 * dr, c + 2 * dc
        if inside(lr, lc) and b[lr][lc] == EMPTY and side(b[mr][mc]) not in ("", side(p)):
            nb = copy.deepcopy(b)
            nb[r][c], nb[mr][mc], nb[lr][lc] = EMPTY, EMPTY, p
            step = path + [(lr, lc)]
            if p in "bw" and lr == crown_row(p):
                out.append(step)  # crowning ends the move
                continue
            more = _jumps(nb, lr, lc, step)
            out += more or [step]
    return out


def legal_moves(b, color: str) -> list[list[tuple[int, int]]]:
    jumps, steps = [], []
    for r in range(8):
        for c in range(8):
            if side(b[r][c]) != color:
                continue
            jumps += _jumps(b, r, c, [(r, c)])
            for dr, dc in directions(b[r][c]):
                if inside(r + dr, c + dc) and b[r + dr][c + dc] == EMPTY:
                    steps.append([(r, c), (r + dr, c + dc)])
    return jumps or steps  # captures are mandatory


def apply(b, path):
    nb = copy.deepcopy(b)
    (r, c), p = path[0], nb[path[0][0]][path[0][1]]
    nb[r][c] = EMPTY
    for (r1, c1), (r2, c2) in zip(path, path[1:]):
        if abs(r2 - r1) == 2:
            nb[(r1 + r2) // 2][(c1 + c2) // 2] = EMPTY
    lr, lc = path[-1]
    nb[lr][lc] = p.upper() if p in "bw" and lr == crown_row(p) else p
    return nb


def is_capture(path) -> bool:
    return abs(path[1][0] - path[0][0]) == 2


def sq(r: int, c: int) -> str:
    return f"{FILES[c]}{8 - r}"


def notation(path) -> str:
    return ("x" if is_capture(path) else "-").join(sq(r, c) for r, c in path)


def render(b) -> str:
    rows = [f"  {' '.join(FILES)}"]
    for r in range(8):
        cells = [b[r][c] if (r + c) % 2 else " " for c in range(8)]
        rows.append(f"{8 - r} {' '.join(cells)} {8 - r}")
    rows.append(f"  {' '.join(FILES)}")
    return "\n".join(rows)


def count(b, color: str) -> tuple[int, int]:
    men = sum(row.count(color) for row in b)
    kings = sum(row.count(color.upper()) for row in b)
    return men, kings


# ----------------------------------------------------------------------------- simulated opponent

def evaluate(b, me: str) -> float:
    score = 0.0
    for r in range(8):
        for c in range(8):
            p = b[r][c]
            if p == EMPTY:
                continue
            v = 1.6 if p in "BW" else 1.0 + 0.04 * (r if p == "b" else 7 - r)  # small push to advance
            score += v if side(p) == me else -v
    return score


def minimax(b, color, me, depth, alpha, beta) -> float:
    moves = legal_moves(b, color)
    if not moves:
        return -100 if color == me else 100
    if depth == 0:
        return evaluate(b, me)
    other = "w" if color == "b" else "b"
    if color == me:
        best = -1e9
        for m in moves:
            best = max(best, minimax(apply(b, m), other, me, depth - 1, alpha, beta))
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    best = 1e9
    for m in moves:
        best = min(best, minimax(apply(b, m), other, me, depth - 1, alpha, beta))
        beta = min(beta, best)
        if beta <= alpha:
            break
    return best


class SimOpponent:
    def __init__(self, color: str, depth: int, seed: int):
        self.color, self.depth, self.rng = color, depth, random.Random(seed)
        self.name = f"simulated (minimax depth {depth})"
        self.last_how = ""

    def choose(self, b, moves):
        other = "w" if self.color == "b" else "b"
        scored = [(minimax(apply(b, m), other, self.color, self.depth - 1, -1e9, 1e9), self.rng.random(), m)
                  for m in moves]
        return max(scored)[2]


# ----------------------------------------------------------------------------- local LLM player

class LLMPlayer:
    SYSTEM = ("You are a strong checkers player. You will be shown the board and a numbered list of legal "
              "moves. Reply with ONLY the number of the move you choose. No other text.")

    def __init__(self, color: str, model: str):
        self.color, self.model, self.name = color, model, model
        self.asked = self.first_try = self.retries = self.fallbacks = self.calls = 0
        self.latency = []
        self.last_how = ""

    def choose(self, b, moves):
        me = "Black (b = man, B = king), moving DOWN the board toward row 1" if self.color == "b" else \
             "White (w = man, W = king), moving UP the board toward row 8"
        bm, bk = count(b, "b")
        wm, wk = count(b, "w")
        listing = "\n".join(f"{i}. {notation(m)}" for i, m in enumerate(moves, 1))
        prompt = (f"{render(b)}\n\nYou play {me}.\nMaterial: Black {bm} men + {bk} kings, "
                  f"White {wm} men + {wk} kings.\n\nLegal moves (x = capture):\n{listing}\n\n"
                  "Prefer moves that win material, crown kings, and don't leave a piece where it can be "
                  f"jumped. Reply with just the number (1-{len(moves)}).")
        self.asked += 1
        for attempt in (1, 2):
            t = time.time()
            reply = ec.chat(self.model, self.SYSTEM, prompt, 0.2 if attempt == 1 else 0.0, 12)
            self.latency.append(time.time() - t)
            self.calls += 1
            m = re.search(r"\d+", reply)
            if m and 1 <= int(m.group()) <= len(moves):
                if attempt == 1:
                    self.first_try += 1
                    self.last_how = "legal first try"
                else:
                    self.retries += 1
                    self.last_how = "legal after retry"
                return moves[int(m.group()) - 1]
            prompt += f"\n\nYour reply {reply[:40]!r} was not a number from 1 to {len(moves)}. Reply with only the number."
        self.fallbacks += 1
        self.last_how = "random fallback"
        return random.choice(moves)


# ----------------------------------------------------------------------------- game

def play(black, white, max_plies: int, verbose: bool) -> dict:
    b, color, since_capture, ply = new_board(), "b", 0, 0
    players = {"b": black, "w": white}
    result = "draw (move limit)"
    history = [{"board": ["".join(row) for row in b]}]
    while ply < max_plies:
        moves = legal_moves(b, color)
        if not moves:
            winner = "White" if color == "b" else "Black"
            result = f"{winner} wins ({'Black' if color == 'b' else 'White'} has no moves)"
            break
        mv = players[color].choose(b, moves)
        piece = b[mv[0][0]][mv[0][1]]
        b = apply(b, mv)
        ply += 1
        history.append({"ply": ply, "color": color, "player": players[color].name,
                        "how": getattr(players[color], "last_how", ""), "notation": notation(mv),
                        "path": mv, "crowned": piece in "bw" and b[mv[-1][0]][mv[-1][1]] in "BW",
                        "captured": [((r1 + r2) // 2, (c1 + c2) // 2) for (r1, c1), (r2, c2) in zip(mv, mv[1:])
                                     if abs(r2 - r1) == 2],
                        "board": ["".join(row) for row in b]})
        since_capture = 0 if is_capture(mv) else since_capture + 1
        if verbose:
            who = "Black" if color == "b" else "White"
            print(f"{DIM}{ply:>3}.{RESET} {who:<5} {notation(mv):<16} {DIM}({players[color].name}){RESET}")
        if since_capture >= 80:
            result = "draw (40 moves each without a capture)"
            break
        color = "w" if color == "b" else "b"
    bm, bk = count(b, "b")
    wm, wk = count(b, "w")
    return {"result": result, "plies": ply, "board": b, "history": history,
            "material": f"Black {bm}+{bk}K vs White {wm}+{wk}K"}


def replay_entry(black, white, g: dict) -> dict:
    return {"title": f"{black.name} vs {white.name}", "black": black.name, "white": white.name,
            "result": g["result"], "material": g["material"], "history": g["history"]}


def show_replay(games: list[dict], enabled: bool) -> None:
    if games and enabled:
        print(f"\n{BOLD}Replay{RESET}  opened {checkers_viewer.write_replay(games)} in your browser")


# ----------------------------------------------------------------------------- tests & checks

def selftest() -> bool:
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")

    b = new_board()
    check("opening: Black has 7 moves", len(legal_moves(b, "b")) == 7)
    e = [[EMPTY] * 8 for _ in range(8)]
    e[2][1], e[3][2], e[4][3] = "b", "w", EMPTY
    e[5][4] = "w"
    e[2][5] = "b"
    ms = legal_moves(e, "b")
    check("capture is mandatory", ms and all(is_capture(m) for m in ms))
    check("double jump is found", any(len(m) == 3 for m in ms))
    after = apply(e, max(ms, key=len))
    check("jumped pieces are removed", count(after, "w") == (0, 0))
    k = [[EMPTY] * 8 for _ in range(8)]
    k[6][1] = "b"
    check("reaching the last row crowns", apply(k, [(6, 1), (7, 0)])[7][0] == "B")
    k2 = [[EMPTY] * 8 for _ in range(8)]
    k2[4][3] = "W"
    check("kings move both ways", len(legal_moves(k2, "w")) == 4)
    g = play(SimOpponent("b", 1, 1), SimOpponent("w", 2, 2), 200, False)
    check(f"sim vs sim game finishes ({g['result']}, {g['plies']} plies)", g["plies"] > 10)
    return ok


def ledger_rows_since(t0: float) -> list[dict]:
    try:
        return [r for r in map(json.loads, ec.LEDGER.read_text().splitlines()) if r.get("ts", 0) >= t0]
    except (OSError, ValueError):
        return []


def check_claude_hook() -> tuple[bool, str]:
    settings = Path.home() / ".claude" / "settings.json"
    footer = HERE.parent / "token_footer.py"
    try:
        registered = "token_footer.py" in settings.read_text()
    except OSError:
        registered = False
    if not registered:
        return False, f"token_footer.py is not registered in {settings}"
    transcripts = sorted((Path.home() / ".claude" / "projects").glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not transcripts:
        return True, "hook registered (no Claude Code transcript yet to test it on)"
    r = subprocess.run([sys.executable, str(footer)], input=json.dumps({"transcript_path": str(transcripts[-1])}),
                       capture_output=True, text=True, timeout=20)
    try:
        msg = json.loads(r.stdout)["systemMessage"]
    except (json.JSONDecodeError, KeyError):
        return False, f"hook ran but produced no footer: {r.stdout[:200]} {r.stderr[:200]}"
    return ("🔴" in msg and "🟢" in msg), "hook registered and working. On your latest Claude Code turn it reports:\n" + \
        "\n".join("        " + line for line in msg.splitlines())


# ----------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help="Ollama model for Black, a comma list, or 'all' (default: best installed)")
    ap.add_argument("--depth", type=int, default=2, help="simulated opponent's search depth (1 = weak, 4 = strong)")
    ap.add_argument("--max-plies", type=int, default=120, help="stop the game after this many half-moves")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--quiet", action="store_true", help="don't print every move")
    ap.add_argument("--selftest", action="store_true", help="only run the rules tests (no Ollama)")
    ap.add_argument("--sim", action="store_true", help="simulated vs simulated game, no Ollama needed")
    ap.add_argument("--no-view", action="store_true", help="don't open the visual replay afterwards")
    args = ap.parse_args()

    print(f"{BOLD}Rules self-test{RESET}")
    rules_ok = selftest()
    if args.selftest:
        sys.exit(0 if rules_ok else 1)
    if args.sim:
        black, white = SimOpponent("b", max(1, args.depth - 1), args.seed), SimOpponent("w", args.depth, args.seed + 1)
        print(f"\n{BOLD}Game: {black.name} (Black) vs {white.name} (White){RESET}")
        g = play(black, white, args.max_plies, not args.quiet)
        print(f"\n{render(g['board'])}\n{BOLD}{g['result']}{RESET} after {g['plies']} plies · {g['material']}")
        show_replay([replay_entry(black, white, g)], not args.no_view)
        sys.exit(0)

    try:
        roster = ec.roster()
        installed = ec.installed_models()
    except ec.OllamaDown as e:
        print(f"\n{RED}FAIL{RESET}  local models: {e}")
        sys.exit(2)
    if args.model == "all":
        models = installed
    elif args.model:
        models = [m.strip() for m in args.model.split(",")]
        missing = [m for m in models if m not in installed]
        if missing:
            print(f"{RED}FAIL{RESET}  not pulled: {', '.join(missing)} (installed: {', '.join(installed)})")
            sys.exit(2)
    else:
        models = roster[:1]

    t0 = time.time()
    reports, replays = [], []
    for model in models:
        print(f"\n{BOLD}Game: {model} (Black) vs simulated opponent depth {args.depth} (White){RESET}")
        llm = LLMPlayer("b", model)
        sim = SimOpponent("w", args.depth, args.seed)
        try:
            g = play(llm, sim, args.max_plies, not args.quiet)
        except ec.OllamaDown as e:
            print(f"{RED}FAIL{RESET}  {model} stopped responding: {e}")
            reports.append((model, llm, None))
            continue
        print(f"\n{render(g['board'])}\n{BOLD}{g['result']}{RESET} after {g['plies']} plies · {g['material']}")
        reports.append((model, llm, g))
        replays.append(replay_entry(llm, sim, g))
    show_replay(replays, not args.no_view)

    # ---- health report
    rows = ledger_rows_since(t0)
    local_tokens = sum(r.get("in", 0) + r.get("out", 0) for r in rows)
    print(f"\n{BOLD}Local model health{RESET}")
    all_ok = rules_ok
    for model, p, g in reports:
        legal = (p.first_try + p.retries) / p.asked if p.asked else 0
        avg = sum(p.latency) / len(p.latency) if p.latency else 0
        mine = [r for r in rows if r.get("model") == model]
        toks = sum(r.get("in", 0) + r.get("out", 0) for r in mine)
        ok = g is not None and p.asked > 0 and legal >= 0.8
        all_ok &= ok
        print(f"  {GREEN + 'PASS' if ok else RED + 'FAIL'}{RESET}  {model:<24} {p.asked} moves · "
              f"{p.first_try} valid first try · {p.retries} after retry · {p.fallbacks} random fallback · "
              f"{avg:.1f}s/reply · {toks:,} tokens")

    print(f"\n{BOLD}Token trackers{RESET}")
    calls = sum(p.calls for _, p, _ in reports)
    ledger_ok = len(rows) >= calls > 0 and local_tokens > 0
    all_ok &= ledger_ok
    print(f"  {GREEN + 'PASS' if ledger_ok else RED + 'FAIL'}{RESET}  🟢 ledger: {calls} model calls made, "
          f"{len(rows)} ledger rows written, {local_tokens:,} tokens recorded ({ec.LEDGER})")
    hook_ok, hook_msg = check_claude_hook()
    all_ok &= hook_ok
    print(f"  {GREEN + 'PASS' if hook_ok else RED + 'FAIL'}{RESET}  🔴 {hook_msg}")

    print(f"\n{RED}🔴 Claude: 0 tokens used by this game (it runs entirely on local models){RESET}")
    print(f"{GREEN}🟢 Local models: {local_tokens:,} tokens handled on this machine{RESET}")
    print(f"\n{BOLD}{GREEN + 'ALL CHECKS PASSED' if all_ok else RED + 'SOME CHECKS FAILED'}{RESET}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
