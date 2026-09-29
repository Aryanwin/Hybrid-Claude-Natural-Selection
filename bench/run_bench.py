#!/usr/bin/env python3
"""
run_bench.py - how many Claude tokens does the hybrid save, and does it still get the answer right?

Every task in tasks.py is solved three ways, then scored by hidden grader tests (graders/) that no approach sees:

  agentic   Claude Code working normally: tools on, writes and runs its own tests until they pass
  oneshot   one minimal Claude call (no tools, short system prompt) that just writes the module
  hybrid    evolve.py: Claude plans / reviews / judges, local models write the code

Claude usage is exact (`claude -p --output-format json`); local usage is Ollama's own token counts.

    python3 bench/run_bench.py --check                     graders vs reference solutions (no models)
    python3 bench/run_bench.py                             full benchmark -> bench/results/results-<ts>.json
    python3 bench/run_bench.py --tasks lru,calc --modes hybrid
    python3 bench/run_bench.py --report bench/results/results-<ts>.json   -> bench/RESULTS.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BENCH = Path(__file__).resolve().parent
REPO = BENCH.parent
sys.path.insert(0, str(BENCH))
from tasks import TASKS  # noqa: E402

ONESHOT_SYSTEM = "You are a precise senior Python engineer. Follow the instructions exactly."
MODES = ("agentic", "oneshot", "hybrid")
LOCK = threading.Lock()


def usage_row(data: dict) -> dict:
    u = data.get("usage", {})
    return {"claude_new": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0),
            "claude_cached": u.get("cache_read_input_tokens", 0), "claude_output": u.get("output_tokens", 0),
            "cost_usd": round(data.get("total_cost_usd", 0.0), 4), "claude_calls": data.get("num_turns", 1)}


def claude(args: list[str], cwd: Path, stdin: str | None, timeout: int, model: str | None) -> dict:
    # --strict-mcp-config: measure a clean Claude Code, without this machine's MCP connectors (which add ~70K
    # tokens of tool definitions to every call and would inflate the agentic and one-shot numbers).
    cmd = ["claude", "-p", *args, "--output-format", "json", "--no-session-persistence", "--strict-mcp-config"]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=timeout)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude -p failed: {(r.stderr or r.stdout)[-500:]}")
    if data.get("is_error"):
        raise RuntimeError(f"claude -p error: {str(data.get('result'))[:300]}")
    return data


def stub(d: Path, module: str) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{module}.py").write_text(f'"""{module}: implement the task here."""\n')


def run_agentic(d: Path, module: str, spec: str, model: str | None) -> dict:
    stub(d, module)
    prompt = (f"{spec}\n\nImplement this in {module}.py in the current directory (standard library only). "
              "Write pytest tests for it and run them until they pass. Don't ask questions.")
    data = claude([prompt, "--permission-mode", "acceptEdits", "--allowedTools",
                   "Read", "Write", "Edit", "Glob", "Grep", "Bash(python3:*)", "Bash(pytest:*)", "Bash(ls:*)"],
                  d, None, 1500, model)
    return usage_row(data)


def run_oneshot(d: Path, module: str, spec: str, model: str | None) -> dict:
    stub(d, module)
    data = claude(["Follow the instructions on stdin.", "--tools", "", "--system-prompt", ONESHOT_SYSTEM], d,
                  f"{spec}\n\nReply with only the complete contents of {module}.py in a single ```python code "
                  "block (standard library only).", 600, model)
    m = re.search(r"```(?:python)?\n(.*?)```", data.get("result", ""), re.S)
    (d / f"{module}.py").write_text(m.group(1) if m else data.get("result", ""))
    return usage_row(data)


def run_hybrid(d: Path, module: str, spec: str, model: str | None) -> dict:
    stub(d, module)
    (d / "tests").mkdir(exist_ok=True)
    (d / "tests" / ".gitkeep").touch()
    (d / ".gitignore").write_text("evolve.log\nsummary.json\ngrade.xml\ngrader_*.py\n__pycache__/\n")
    git = ["git", "-c", "user.name=bench", "-c", "user.email=bench@localhost"]
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "stub"]):
        subprocess.run(git + cmd, cwd=d, check=True, capture_output=True)
    cmd = [sys.executable, str(REPO / "evolve.py"), spec, "--files", f"{module}.py", "--summary-json", str(d / "summary.json")]
    if model:
        cmd += ["--claude-model", model]
    with open(d / "evolve.log", "w") as log:
        subprocess.run(cmd, cwd=d, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
    s = json.loads((d / "summary.json").read_text())
    return {"claude_new": s["claude_new"], "claude_cached": s["claude_cached"], "claude_output": s["claude_output"],
            "cost_usd": s["claude_cost_usd"], "claude_calls": s["claude_calls"], "local_tokens": s["local_tokens"],
            "solved_own_tests": s["solved"], "rounds": s["rounds"]}


def grade(d: Path, module: str) -> tuple[int, int]:
    shutil.copy(BENCH / "graders" / f"test_{module}.py", d / f"grader_{module}.py")
    env = {**os.environ, "PYTHONPATH": str(d), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--junitxml=grade.xml",
                        f"grader_{module}.py"], cwd=d, env=env, capture_output=True, timeout=180)
        cases = list(ET.parse(d / "grade.xml").getroot().iter("testcase"))
    except (subprocess.TimeoutExpired, ET.ParseError, FileNotFoundError):
        return 0, len(re.findall(r"^def test_", (BENCH / "graders" / f"test_{module}.py").read_text(), re.M))
    failed = sum(1 for c in cases if any(ch.tag in ("failure", "error") for ch in c))
    expected = len(re.findall(r"^def test_", (BENCH / "graders" / f"test_{module}.py").read_text(), re.M))
    return len(cases) - failed, max(len(cases), expected)  # a module that won't import counts as all failed


RUNNERS = {"agentic": run_agentic, "oneshot": run_oneshot, "hybrid": run_hybrid}


def run_one(mode, module, kind, spec, root, model, results, out):
    d, t0 = root / mode / module, time.time()
    row = {"task": module, "kind": kind, "mode": mode, "claude_new": 0, "claude_cached": 0, "claude_output": 0,
           "cost_usd": 0.0, "claude_calls": 0, "local_tokens": 0, "note": ""}
    try:
        row.update(RUNNERS[mode](d, module, spec, model))
    except Exception as e:  # one broken run must not stop the benchmark
        row["note"] = f"{type(e).__name__}: {e}"[:300]
    row["passed"], row["total"] = grade(d, module) if d.exists() else (0, 0)
    row["seconds"] = round(time.time() - t0, 1)
    with LOCK:
        results.append(row)
        out.write_text(json.dumps(results, indent=2))
        print(f"[{time.strftime('%H:%M:%S')}] {mode:<8} {module:<13} graders {row['passed']}/{row['total']}  "
              f"claude {row['claude_new'] + row['claude_cached']:>9,} (new {row['claude_new']:,})  "
              f"local {row['local_tokens']:>7,}  {row['seconds']:>6.0f}s {row['note'][:80]}", flush=True)


def check() -> None:
    ok = True
    for module, _, _ in TASKS:
        d = Path.home() / ".cache" / "evolve" / "bench" / "check" / module
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        shutil.copy(BENCH / "reference" / f"{module}.py", d)
        p, t = grade(d, module)
        ok &= p == t > 0
        print(f"  {'PASS' if p == t > 0 else 'FAIL'}  {module:<13} {p}/{t}")
    sys.exit(0 if ok else 1)


# ----------------------------------------------------------------------------- report

def fmt(n: float) -> str:
    return f"{n / 1000:,.1f}K" if n >= 1000 else f"{n:,.0f}"


def report(path: Path) -> str:
    rows = json.loads(path.read_text())
    by = {(r["task"], r["mode"]): r for r in rows}
    modes = [m for m in MODES if any(r["mode"] == m for r in rows)]
    tasks = [t for t, _, _ in TASKS if any(r["task"] == t for r in rows)]
    names = {"agentic": "Claude Code (agentic)", "oneshot": "Claude one-shot", "hybrid": "Hybrid (this repo)"}

    out = ["# Benchmark results", "",
           f"{len(tasks)} tasks, each solved three ways and scored by hidden grader tests "
           "(`bench/graders/`, verified against `bench/reference/`). Claude tokens are exact "
           "(`claude -p --output-format json`); local tokens are Ollama's own counts. "
           "\"Claude tokens\" = new input + cache writes + output + cache reads; cache reads cost ~10% of new input.", ""]
    out += ["## Summary", "", "| | " + " | ".join(names[m] for m in modes) + " |", "|---" * (len(modes) + 1) + "|"]

    def total(m, key):
        return sum(by[(t, m)].get(key, 0) for t in tasks if (t, m) in by)

    def solved(m):
        return sum(1 for t in tasks if (t, m) in by and by[(t, m)]["passed"] == by[(t, m)]["total"] > 0)

    lines = {
        "Tasks fully correct": lambda m: f"{solved(m)}/{len(tasks)}",
        "Grader tests passed": lambda m: f"{total(m, 'passed')}/{total(m, 'total')}",
        "Claude tokens (total)": lambda m: fmt(total(m, "claude_new") + total(m, "claude_cached")),
        "…of which new (not cache reads)": lambda m: fmt(total(m, "claude_new")),
        "…of which Claude wrote (output)": lambda m: fmt(total(m, "claude_output")),
        "Claude cost at API prices": lambda m: f"${total(m, 'cost_usd'):.2f}",
        "Local tokens (free)": lambda m: fmt(total(m, "local_tokens")),
        "Wall time (sum)": lambda m: f"{total(m, 'seconds') / 60:.0f} min",
    }
    for label, f in lines.items():
        out.append(f"| {label} | " + " | ".join(f(m) for m in modes) + " |")

    if "hybrid" in modes:
        out += ["", "**Hybrid vs. the others** (Claude cost at API prices, which weights output and cache reads correctly):", ""]
        h = total("hybrid", "cost_usd")
        for m in (x for x in modes if x != "hybrid"):
            o = total(m, "cost_usd")
            if o:
                out.append(f"- vs {names[m]}: {'saves' if h < o else 'costs'} {abs(1 - h / o):.0%} "
                           f"(${h:.2f} vs ${o:.2f}); Claude tokens {fmt(total('hybrid', 'claude_new') + total('hybrid', 'claude_cached'))} "
                           f"vs {fmt(total(m, 'claude_new') + total(m, 'claude_cached'))}")

    out += ["", "## Per task", "", "Graders passed · Claude tokens (total / new) · cost" +
            (" · local tokens" if "hybrid" in modes else ""), "",
            "| Task | Kind | " + " | ".join(names[m] for m in modes) + " |", "|---|---" + "|---" * len(modes) + "|"]
    for t in tasks:
        cells = []
        for m in modes:
            r = by.get((t, m))
            if not r:
                cells.append("–")
                continue
            mark = "✅" if r["passed"] == r["total"] > 0 else "❌"
            c = f"{mark} {r['passed']}/{r['total']} · {fmt(r['claude_new'] + r['claude_cached'])} / {fmt(r['claude_new'])} · ${r['cost_usd']:.3f}"
            if m == "hybrid":
                c += f" · {fmt(r['local_tokens'])} local"
            if r["note"]:
                c += " ⚠️"
            cells.append(c)
        kind = next(k for n, k, _ in TASKS if n == t)
        out.append(f"| `{t}` | {kind} | " + " | ".join(cells) + " |")
    notes = [f"- `{r['task']}` {r['mode']}: {r['note']}" for r in rows if r["note"]]
    if notes:
        out += ["", "Errors during runs:", ""] + notes
    return "\n".join(out) + "\n"


def compare(named: list[tuple[str, Path]]) -> str:
    """Side-by-side summary of several result files (e.g. the same benchmark with different Claude models)."""
    runs = [(label, json.loads(p.read_text())) for label, p in named]
    names = {"agentic": "Claude Code (agentic)", "oneshot": "Claude one-shot", "hybrid": "Hybrid"}
    head = "| Approach | Metric | " + " | ".join(label for label, _ in runs) + " |"
    out = ["## By Claude model", "", head, "|---|---" + "|---" * len(runs) + "|"]
    for m in MODES:
        sel = [[r for r in rows if r["mode"] == m] for _, rows in runs]
        if not all(sel):
            continue
        metrics = {
            "Tasks fully correct": lambda rs: f"{sum(r['passed'] == r['total'] > 0 for r in rs)}/{len(rs)}",
            "Grader tests passed": lambda rs: f"{sum(r['passed'] for r in rs)}/{sum(r['total'] for r in rs)}",
            "Claude tokens": lambda rs: fmt(sum(r["claude_new"] + r["claude_cached"] for r in rs)),
            "Claude output tokens": lambda rs: fmt(sum(r["claude_output"] for r in rs)),
            "Claude cost (API prices)": lambda rs: f"${sum(r['cost_usd'] for r in rs):.2f}",
            "Local tokens": lambda rs: fmt(sum(r["local_tokens"] for r in rs)),
            "Wall time": lambda rs: f"{sum(r['seconds'] for r in rs) / 60:.0f} min",
        }
        for i, (label, f) in enumerate(metrics.items()):
            if label == "Local tokens" and m != "hybrid":
                continue
            out.append(f"| {names[m] if i == 0 else ''} | {label} | " + " | ".join(f(rs) for rs in sel) + " |")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", default="all", help="comma list of task names (default: all)")
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--workers", type=int, default=4, help="parallel Claude-only runs")
    ap.add_argument("--claude-model", help="same Claude model for every mode (default: your Claude Code default)")
    ap.add_argument("--out", help="results JSON (default bench/results/results-<timestamp>.json)")
    ap.add_argument("--check", action="store_true", help="verify graders against the reference solutions")
    ap.add_argument("--report", help="write bench/RESULTS.md from a results JSON")
    ap.add_argument("--compare", nargs="+", metavar="LABEL=FILE",
                    help="side-by-side table of several result files, e.g. sonnet=a.json haiku=b.json")
    args = ap.parse_args()

    if args.compare:
        print(compare([(x.split("=", 1)[0], Path(x.split("=", 1)[1])) for x in args.compare]))
        return
    if args.check:
        check()
    if args.report:
        md = report(Path(args.report))
        (BENCH / "RESULTS.md").write_text(md)
        print(md)
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    root = Path.home() / ".cache" / "evolve" / "bench" / stamp
    out = Path(args.out) if args.out else BENCH / "results" / f"results-{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    wanted = None if args.tasks == "all" else set(args.tasks.split(","))
    tasks = [t for t in TASKS if wanted is None or t[0] in wanted]
    modes = [m for m in args.modes.split(",") if m]
    results: list[dict] = []
    print(f"{len(tasks)} tasks x {modes} -> {out}\nwork dirs: {root}", flush=True)

    # Hybrid runs share the local GPU, so they go one at a time; Claude-only runs overlap with them.
    hybrid = threading.Thread(target=lambda: [run_one("hybrid", n, k, s, root, args.claude_model, results, out)
                                              for n, k, s in tasks] if "hybrid" in modes else None)
    hybrid.start()
    with ThreadPoolExecutor(args.workers) as ex:
        for m in (m for m in modes if m != "hybrid"):
            for n, k, s in tasks:
                ex.submit(run_one, m, n, k, s, root, args.claude_model, results, out)
    hybrid.join()
    (BENCH / "RESULTS.md").write_text(report(out))
    print(f"\nDone. Results: {out}\nReport:  {BENCH / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
