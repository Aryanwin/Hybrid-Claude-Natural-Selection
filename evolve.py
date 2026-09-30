#!/usr/bin/env python3
"""
evolve.py - Darwinian coding loop: a roster of local models evolves competing threads, Claude steers.

    task -> Claude: spec + visible tests + hidden tests                     (1 Claude call)
         -> N threads (lineages), each owned by one local model from --models
         -> every round (all local, free):
              - each thread breeds children: mutations of its fittest attempt + test failures
              - crossover: if two threads pass complementary tests, one child merges them
              - pytest scores every child in its own git worktree
              - selection: each thread keeps its fittest; duplicate threads are dropped;
                threads with no progress for --patience rounds die and fresh ones replace them
         -> every --review-every rounds Claude reads a compact digest of all threads and
            kills, keeps, refines (a targeted hint) or forks them onto another model  (1 call each)
         -> a thread stuck 1-2 tests from passing gets an early review, with an optional code snippet
         -> visible-test passers must also pass the hidden tests (catches test-gaming); when they fail only
            the hidden ones, Claude referees: corrects wrong hidden tests, or sends the thread a hint
         -> 2+ finalists: Claude picks the winner from the diffs                     (1 call)
         -> winner + tests written into your working tree for you to review with `git diff`

Run from anywhere inside a git repo (commit or stash your work first):

    python evolve.py "Add a slugify(title) function that ..." --files mypkg/text.py

Needs: Python 3.9+, git, pytest, Ollama running locally, and Claude Code (`claude`) on PATH
(not needed if you pass --tests and --no-claude). Standard library only.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses
import difflib
import hashlib
import json
import os
import py_compile
import queue
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# ----------------------------------------------------------------------------- config

_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_URL = _host if _host.startswith("http") else f"http://{_host}"

# Models, slots and context come from this machine's hardware profile (hardware.py / evolve.config.json).
# Different model families make different mistakes, which is what keeps the population diverse.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hardware  # noqa: E402

CFG = hardware.load_config()

LOCAL_SYSTEM = """You are an expert Python developer working on an existing codebase.
You change code so that it satisfies a spec and passes the given tests.

Rules:
- Output ONLY the complete, final content of every file you change, in exactly this format:

### FILE: path/to/file.py
```python
<entire file content>
```

- Only output files from the EDITABLE FILES list. Always output the whole file, never a fragment or a diff.
- Never edit or special-case the tests. Do not hard-code expected outputs. Write a general implementation.
- Keep existing behaviour that the task does not ask you to change.
- No explanations outside the file blocks."""

# ----------------------------------------------------------------------------- helpers

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def die(msg: str) -> None:
    print(f"\nerror: {msg}", file=sys.stderr)
    sys.exit(2)


def run(cmd, cwd=None, timeout=None, input=None, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, input=input, env=env)


def tag(text: str, name: str) -> str | None:
    m = re.search(rf"<{name}>(.*?)</{name}>", text, re.S)
    return m.group(1).strip() if m else None


def strip_fences(code: str) -> str:
    code = code.strip()
    m = re.match(r"^```[\w+-]*\n(.*?)\n?```$", code, re.S)
    return (m.group(1) if m else code).rstrip() + "\n"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:40] or "task"


def clip(text: str, n: int, tail: bool = False) -> str:
    if len(text) <= n:
        return text
    return "...(truncated)\n" + text[-n:] if tail else text[:n] + "\n...(truncated)"


def fmt_files(files: dict[str, str]) -> str:
    return "\n\n".join(f"### FILE: {p}\n```python\n{c}```" for p, c in files.items())


def unified_diff(old: dict[str, str], new: dict[str, str]) -> str:
    out = []
    for p in sorted(set(old) | set(new)):
        a, b = old.get(p, ""), new.get(p, "")
        if a != b:
            out += difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                                        f"a/{p}", f"b/{p}")
    return "".join(out)


def changed_lines(diff: str) -> int:
    return sum(1 for l in diff.splitlines()
               if l[:1] in "+-" and not l.startswith(("+++", "---")))


# ----------------------------------------------------------------------------- models

class Usage:
    """Exact counts: Claude's from `claude -p --output-format json`, local ones from Ollama's eval counts."""
    claude_calls = 0
    claude_new = 0        # input + cache writes + output
    claude_cached = 0     # cache reads (billed at a fraction)
    claude_output = 0
    claude_cost = 0.0     # USD at API list price, as reported by Claude Code
    local_calls = 0
    local_tokens = 0      # prompt + generated tokens processed locally
    local_output = 0


# The planner / reviewer / judge never use tools, so skip Claude Code's tool definitions and default system
# prompt, and don't load the user's MCP connectors (Gmail, Drive, ... add ~70K tokens of tool definitions per
# call): this cuts each call's fixed overhead from ~28-100K tokens to ~1.3K.
CLAUDE_SYSTEM = ("You are a precise senior software engineer acting as planner, reviewer and judge in an automated "
                 "pipeline. Follow the instructions exactly and reply in the requested format, with text only.")


def ask_claude(prompt: str, args, name: str) -> str:
    if args.no_claude:
        die("this step needs Claude but --no-claude is set")
    if not shutil.which("claude"):
        die("`claude` (Claude Code) not found on PATH. Install it or use --tests + --no-claude.")
    cmd = ["claude", "-p", "--output-format", "json", "--tools", "", "--system-prompt", CLAUDE_SYSTEM,
           "--no-session-persistence", "--strict-mcp-config", "Follow the instructions given on stdin."]
    if args.claude_model:
        cmd += ["--model", args.claude_model]
    log(f"Claude: {name} ...")
    (args.run_dir / f"claude_{name}_prompt.txt").write_text(prompt)
    try:
        r = run(cmd, input=prompt, timeout=900)
    except subprocess.TimeoutExpired:
        die(f"Claude timed out during {name}")
    (args.run_dir / f"claude_{name}_response.txt").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr)
    if r.returncode != 0:
        why = (r.stderr.strip() or r.stdout.strip())[-2000:]
        hint = "\nRun `claude` once in a terminal and log in, then retry." if "login" in why.lower() else ""
        die(f"`claude -p` failed during {name}:\n{why}{hint}")
    Usage.claude_calls += 1
    try:
        data = json.loads(r.stdout)
        u = data.get("usage", {})
        Usage.claude_new += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0)
        Usage.claude_cached += u.get("cache_read_input_tokens", 0)
        Usage.claude_output += u.get("output_tokens", 0)
        Usage.claude_cost += data.get("total_cost_usd", 0.0)
        return data.get("result", "")
    except json.JSONDecodeError:  # older Claude Code without JSON output: estimate
        Usage.claude_new += (len(prompt) + len(r.stdout)) // 4
        return r.stdout


LEDGER = Path.home() / ".cache" / "evolve" / "ledger.jsonl"


def record_local(model: str, data: dict) -> None:
    """Append Ollama's exact token counts to the ledger read by token_footer.py."""
    row = {"ts": time.time(), "model": model, "source": "evolve",
           "in": data.get("prompt_eval_count", 0), "out": data.get("eval_count", 0)}
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "a") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass


def claude_left(args) -> int:
    return 0 if args.no_claude else args.claude_budget - Usage.claude_calls


def ask_local(messages: list[dict], args, model: str, temperature: float) -> str:
    body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": temperature, "num_ctx": args.ctx, "num_predict": args.max_tokens},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=args.local_timeout) as resp:
        data = json.load(resp)
    record_local(model, data)
    text = data.get("message", {}).get("content", "")
    Usage.local_calls += 1
    Usage.local_tokens += data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
    Usage.local_output += data.get("eval_count", 0)
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S)


def check_ollama(args) -> None:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
            names = [m["name"] for m in json.load(resp).get("models", [])]
    except (urllib.error.URLError, OSError):
        die(f"can't reach Ollama at {OLLAMA_URL}. Start it with `python3 start_ollama.py`.")
    missing = [m for m in args.models if (m if ":" in m else m + ":latest") not in names]
    if missing:
        die("model(s) not pulled: " + ", ".join(missing) + "\nRun: " +
            " && ".join(f"ollama pull {m}" for m in missing) +
            f"\nAvailable: {', '.join(names) or 'none'}")


# ----------------------------------------------------------------------------- population

@dataclass
class Candidate:
    id: str
    files: dict
    thread: str = "-"
    model: str = ""
    parent: str = "-"
    kind: str = "fresh"          # fresh | mutant | cross
    passed: int = 0
    total: int = 1
    feedback: str = ""
    diff: str = ""
    note: str = ""               # gen-error | no-files | syntax | hidden | rejected
    passed_tests: frozenset = frozenset()
    failed_tests: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.total > 0 and self.passed == self.total and not self.note

    def score(self):
        # Most tests passed first, then clean (no flags), then smallest change (less churn = less risk).
        frac = self.passed / self.total if self.total else 0.0
        return (frac, 0 if self.note else 1, -changed_lines(self.diff))

    def progress(self):
        return self.score()[:2]


@dataclass
class Thread:
    """One lineage: a local model repeatedly improving its own fittest attempt."""
    id: str
    model: str
    born: int
    origin: str = "seed"         # seed | refill | fork:T2
    best: Candidate | None = None
    hint: str = ""               # Claude's steer for this thread only
    stale: int = 0               # rounds without progress
    alive: bool = True
    fate: str = ""
    history: list = field(default_factory=list)

    def fitness(self):
        return self.best.score() if self.best else (-1.0, 0, 0)


@dataclass
class Job:
    cid: str
    thread: Thread
    parent: Candidate | None
    mate: Candidate | None
    temperature: float


def parse_files(text: str, editable: set[str], base: dict[str, str]) -> dict[str, str] | None:
    found = {}
    for m in re.finditer(r"###\s*FILE:\s*`?([^\n`]+?)`?\s*\n```[\w+-]*\n(.*?)\n```", text, re.S):
        path = m.group(1).strip().lstrip("./")
        if path in editable:
            found[path] = m.group(2).rstrip() + "\n"
    if not found:
        return None
    return {**base, **found}


def build_prompt(ctx, base_files: dict[str, str], thread_hint: str, extra: str = "") -> list[dict]:
    parts = [f"TASK:\n{ctx.task}", f"SPEC:\n{ctx.spec}"]
    if ctx.context_files:
        parts.append("READ-ONLY CONTEXT FILES (do not output these):\n" + fmt_files(ctx.context_files))
    parts.append("TESTS YOUR CODE MUST PASS (read-only; run with `python -m pytest` from the repo root):\n"
                 + fmt_files({ctx.visible_path: ctx.visible_tests}))
    for h in (ctx.hint, thread_hint):
        if h:
            parts.append(f"REVIEWER HINT (from a senior engineer, follow it):\n{h}")
    parts.append("EDITABLE FILES (current content):\n" + fmt_files(base_files))
    if extra:
        parts.append(extra)
    parts.append("Now output the complete updated editable file(s).")
    return [{"role": "system", "content": LOCAL_SYSTEM}, {"role": "user", "content": "\n\n".join(parts)}]


def generate(ctx, args, job: Job) -> Candidate:
    t, parent, mate = job.thread, job.parent, job.mate
    if parent is None:
        base, extra, kind, pid = ctx.original, "", "fresh", "-"
    elif mate is None:
        base, kind, pid = parent.files, "mutant", parent.id
        extra = ("YOUR PREVIOUS ATTEMPT is shown above as the editable files. It "
                 f"passed {parent.passed}/{parent.total} tests. Failure output:\n```\n{parent.feedback}\n```\n"
                 "Find the root cause and fix it. Keep what already works.")
    else:
        base, kind, pid = parent.files, "cross", f"{parent.id}+{mate.id}"
        only_a = sorted(parent.passed_tests - mate.passed_tests)
        only_b = sorted(mate.passed_tests - parent.passed_tests)
        extra = ("TWO PREVIOUS ATTEMPTS pass DIFFERENT tests. Attempt A is shown above as the editable files "
                 f"({parent.passed}/{parent.total} passing). Attempt B ({mate.passed}/{mate.total} passing), "
                 f"as a diff against the original:\n```diff\n{clip(mate.diff, 6000)}```\n"
                 f"Tests only A passes: {', '.join(only_a) or '-'}\n"
                 f"Tests only B passes: {', '.join(only_b) or '-'}\n"
                 "Combine them: keep what makes A pass its tests and adopt the parts of B that make B pass the "
                 "others. Write one coherent implementation.")
    msgs = build_prompt(ctx, base, t.hint, extra)
    est = sum(len(m["content"]) for m in msgs) / 3.5 + args.max_tokens
    if est > args.ctx:
        log(f"  warning: {job.cid} prompt is ~{int(est)} tokens, over --ctx {args.ctx}; the model will lose "
            "context. Use fewer/smaller files or raise --ctx.")
    common = dict(thread=t.id, model=t.model, parent=pid, kind=kind)
    try:
        text = ask_local(msgs, args, t.model, job.temperature)
    except Exception as e:  # network error, timeout, bad JSON
        return Candidate(job.cid, dict(base), feedback=f"generation failed: {e}", note="gen-error", **common)
    (args.run_dir / f"{job.cid}_{t.id}.txt").write_text(text)
    files = parse_files(text, set(ctx.original), base)
    if files is None:
        return Candidate(job.cid, dict(base), note="no-files",
                         feedback="Your reply contained no '### FILE:' blocks for the editable files.", **common)
    return Candidate(job.cid, files, **common)


def generate_all(jobs: list[Job], ctx, args, order: list[str]) -> list[Candidate]:
    """One model at a time (only one fits in memory), its jobs in parallel Ollama slots."""
    out = []
    for model in order:
        js = [j for j in jobs if j.thread.model == model]
        log(f"  {model}: {len(js)} candidate(s)")
        with cf.ThreadPoolExecutor(min(len(js), args.parallel)) as ex:
            out += list(ex.map(lambda j: generate(ctx, args, j), js))
    return out


# ----------------------------------------------------------------------------- evaluation

def reset_slot(slot: Path) -> None:
    run(["git", "checkout", "-f", "--", "."], cwd=slot)
    run(["git", "clean", "-fdxq"], cwd=slot)


def write_files(slot: Path, files: dict[str, str]) -> None:
    for p, c in files.items():
        dest = slot / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(c)


def pytest(slot: Path, targets: list[str], timeout: int):
    """Returns (passed, total, output tail, passed test names, failed test names)."""
    report = slot / ".evolve_report.xml"
    env = dict(os.environ)
    paths = [str(slot / "src"), str(slot)] if (slot / "src").is_dir() else [str(slot)]
    # Put the worktree first on sys.path so an editable install of the main repo can't shadow it.
    env["PYTHONPATH"] = os.pathsep.join(paths + [env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider",
           f"--junitxml={report}", *targets]
    try:
        r = run(cmd, cwd=slot, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return 0, 1, f"Tests timed out after {timeout}s (infinite loop or very slow code?).", frozenset(), []
    out = (r.stdout + r.stderr)[-3000:]
    try:
        root = ET.parse(report).getroot()
    except (ET.ParseError, FileNotFoundError):
        return 0, 1, out, frozenset(), []
    passed, failed = set(), []
    for tc in root.iter("testcase"):
        kids = {ch.tag for ch in tc}
        if "skipped" in kids:
            continue
        name = tc.get("name", "?")
        if kids & {"failure", "error"}:
            failed.append(name)
        else:
            passed.add(name)
    total = len(passed) + len(failed)
    if total == 0:
        return 0, 1, out, frozenset(), []
    return len(passed), total, out, frozenset(passed), failed


def evaluate(c: Candidate, slot: Path, ctx, args) -> Candidate:
    c.diff = unified_diff(ctx.original, c.files)
    if c.note in ("gen-error", "no-files"):
        return c
    c.note = "rejected" if c.note == "rejected" else ""
    reset_slot(slot)
    write_files(slot, c.files)
    write_files(slot, {ctx.visible_path: ctx.visible_tests})  # always the pristine tests
    for p in c.files:
        if p.endswith(".py"):
            try:
                py_compile.compile(str(slot / p), doraise=True)
            except py_compile.PyCompileError as e:
                c.passed, c.total, c.feedback, c.note = 0, 1, f"SyntaxError:\n{e.msg}", "syntax"
                c.passed_tests, c.failed_tests = frozenset(), []
                return c
    c.passed, c.total, c.feedback, c.passed_tests, c.failed_tests = \
        pytest(slot, [ctx.visible_path], args.test_timeout)
    return c


def evaluate_all(pop: list[Candidate], slots: list[Path], ctx, args) -> list[Candidate]:
    free = queue.Queue()
    for s in slots:
        free.put(s)

    def one(c):
        s = free.get()
        try:
            return evaluate(c, s, ctx, args)
        finally:
            free.put(s)

    with cf.ThreadPoolExecutor(len(slots)) as ex:
        return list(ex.map(one, pop))


def final_check(c: Candidate, slot: Path, ctx, args) -> tuple[bool, str]:
    """Hidden tests (+ optionally your whole existing suite). Output is never shown to the local models."""
    if not ctx.hidden_tests and not args.full_suite:
        return True, ""
    reset_slot(slot)
    write_files(slot, c.files)
    tests = {ctx.visible_path: ctx.visible_tests}
    targets = []
    if ctx.hidden_tests:
        tests[ctx.hidden_path] = ctx.hidden_tests
        targets.append(ctx.hidden_path)
    write_files(slot, tests)
    if args.full_suite:
        targets = []  # let pytest discover everything, including the new tests
    passed, total, out, _, _ = pytest(slot, targets, args.test_timeout * 3)
    return passed == total, out


# ----------------------------------------------------------------------------- Claude steps

def claude_plan(ctx, args, repo_listing: str) -> None:
    prompt = f"""You are the PLANNER in a coding pipeline. Several small local models (~7-30B parameters)
will write the code in competing threads; you write the spec and the tests. Your tests are the ONLY signal
used to choose between their attempts, so make them precise, deterministic and thorough. Give tests
descriptive names: they are used to tell which attempts solve which parts of the problem.
Do not use any tools.

TASK:
{args.task}

EDITABLE FILES (the local models may change only these; empty = new file):
{fmt_files(ctx.original)}

READ-ONLY CONTEXT FILES:
{fmt_files(ctx.context_files) if ctx.context_files else "(none)"}

REPOSITORY FILES:
{repo_listing}

Tests run with `python -m pytest` from the repository root, with the repo root{" and src/" if ctx.src_layout else ""}
on sys.path. The visible tests will be saved as {ctx.visible_path}, the hidden tests as {ctx.hidden_path}.
Use only the standard library and packages the project already uses.

Reply with exactly these three sections and nothing else:
<spec>
Numbered, concrete instructions for the local models: exact function/class signatures, behaviour,
edge cases, error handling, constraints. Under 300 words.
</spec>
<tests>
A complete pytest file for the main behaviour and edge cases. The local models see this file.
</tests>
<hidden_tests>
A complete pytest file that checks the same behaviour with DIFFERENT inputs, to catch implementations
that special-case the visible tests. The local models never see this file.
</hidden_tests>"""
    out = ask_claude(prompt, args, "plan")
    spec, tests, hidden = tag(out, "spec"), tag(out, "tests"), tag(out, "hidden_tests")
    if not spec or not tests:
        die(f"couldn't parse Claude's plan; see {args.run_dir}/claude_plan_response.txt")
    ctx.spec, ctx.visible_tests = spec, strip_fences(tests)
    ctx.hidden_tests = strip_fences(hidden) if hidden else ""


def thread_digest(t: Thread, args) -> str:
    b = t.best
    head = (f"### {t.id}  model={t.model}  origin={t.origin}  born=round {t.born}  "
            f"stale={t.stale}\nprogress by round: {' -> '.join(t.history) or '-'}")
    if t.hint:
        head += f"\ncurrent hint: {t.hint}"
    if b is None:
        return head + "\n(no attempt yet)"
    if near_miss(t, args):
        head += "\nNEAR MISS: stuck 1-2 tests from passing. A code snippet is allowed for this thread."
    flag = f" [{b.note}]" if b.note else ""
    return (f"{head}\nbest attempt {b.id} ({b.kind}): {b.passed}/{b.total} tests{flag}, "
            f"{changed_lines(b.diff)} changed lines\n"
            f"failing: {', '.join(b.failed_tests[:10]) or '-'}\n"
            f"```diff\n{clip(b.diff, args.review_diff_chars) or '(no changes)'}```\n"
            f"failure output (tail):\n```\n{clip(b.feedback, args.review_fail_chars, tail=True)}\n```")


def claude_review(ctx, threads: list[Thread], args, rnd: int) -> bool:
    """Claude reads every live thread and decides its fate. Returns True if the visible tests changed."""
    alive = [t for t in threads if t.alive]
    room = args.max_threads - len(alive)
    prompt = f"""You supervise an evolutionary coding run. Several small local models each evolve their own
thread (lineage) of attempts; each round a thread mutates its best attempt using the test failures.
Local compute is free, your tokens are not: your job is to spend the local compute wisely.
Do not use any tools.

TASK:
{ctx.task}

SPEC:
{ctx.spec}

VISIBLE TESTS ({ctx.visible_path}):
```python
{clip(ctx.visible_tests, 5000)}```

AVAILABLE LOCAL MODELS: {", ".join(args.models)}
ROUND {rnd} of {args.rounds}. Live threads: {len(alive)}. Forks allowed this review: {max(0, room)}.

{chr(10).join(thread_digest(t, args) for t in alive)}

For every live thread choose one action:
- keep:   making real progress, leave it alone.
- kill:   dead end (wrong approach, hard-coding test cases, stuck on the same failure, redundant with a
          better thread). Killed threads are replaced by fresh local attempts for free.
- refine: promising but stuck. Give a pointed hint (under 80 words) naming the specific bug and fix.
          Do not write the whole solution. For a thread marked NEAR MISS you may also add "snippet": at most
          25 lines of code showing the fix (e.g. the corrected function or the reordered grammar rules),
          because small models often can't carry out a structural fix from words alone.
- fork:   copy this thread's best attempt into a NEW thread, usually on a different model (set "model"),
          optionally with a hint. Use when the approach is right but the model seems to be the bottleneck.
Keep at least one thread alive.

Reply exactly as:
<decisions>
{{"threads": [{{"id": "T1", "action": "keep|kill|refine|fork", "hint": "...", "snippet": "NEAR MISS refine only",
               "model": "for fork only"}}],
 "global_hint": "optional, short, sent to every thread; empty if not needed"}}
</decisions>
<fixed_tests>complete corrected visible test file, ONLY if the tests themselves are wrong</fixed_tests>"""
    out = ask_claude(prompt, args, f"review_r{rnd}")
    raw = tag(out, "decisions") or out
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        data = json.loads(m.group()) if m else {}
    except json.JSONDecodeError:
        data = {}
    if not data:
        log("  couldn't parse Claude's review; keeping all threads.")
    by_id = {t.id: t for t in alive}
    for d in data.get("threads", []):
        t = by_id.get(str(d.get("id", "")).strip())
        action = str(d.get("action", "keep")).lower().strip()
        hint = str(d.get("hint") or "").strip()
        if t is None:
            continue
        if action == "kill":
            t.alive, t.fate = False, f"killed by Claude r{rnd}: {hint or 'dead end'}"
            log(f"  {t.id} ({t.model}) killed. {hint}")
        elif action == "refine" and hint:
            snippet = str(d.get("snippet") or "").strip().strip("`").removeprefix("python").strip()
            if snippet and near_miss(t, args):
                snippet = "\n".join(snippet.splitlines()[:25])
                hint += f"\nApply this fix (adapt names to your code):\n```python\n{snippet}\n```"
            t.hint, t.stale = hint, 0
            log(f"  {t.id} ({t.model}) refined{' with a code snippet' if snippet else ''}: {hint.splitlines()[0]}")
        elif action == "fork" and t.best and room > 0:
            model = d.get("model") if d.get("model") in args.models else other_model(t.model, args)
            child = ctx.spawn(model, f"fork:{t.id}", rnd, hint)
            child.best = dataclasses.replace(t.best, thread=child.id)
            child.history = [f"{t.best.passed}/{t.best.total}"]
            room -= 1
            log(f"  {t.id} forked into {child.id} on {model}. {hint}")
        else:
            log(f"  {t.id} ({t.model}) kept.")
    gh = str(data.get("global_hint") or "").strip()
    if gh:
        ctx.hint = gh
        log(f"  Global hint: {gh}")
    if not any(t.alive for t in threads):
        leader = max(threads, key=lambda t: t.fitness())
        leader.alive, leader.fate = True, ""
        log(f"  Claude killed every thread; reviving the leader {leader.id}.")
    fixed = tag(out, "fixed_tests")
    if fixed and "def test" in fixed:
        log("  Claude corrected the visible tests.")
        ctx.visible_tests = strip_fences(fixed)
        return True
    return False


def claude_dispute(ctx, c: Candidate, out: str, args, rnd: int) -> str:
    """A candidate passes every visible test but fails hidden ones. Hidden tests are written in one shot and are
    sometimes wrong, which silently rejects correct code, so Claude referees before the rejection sticks.
    Returns "tests" (hidden tests were wrong and have been replaced) or "code" (c.feedback now holds a hint)."""
    prompt = f"""A candidate passes ALL visible tests but fails some of the HIDDEN tests you wrote for this spec.
Hidden tests are written without running them, so they are sometimes wrong. Decide who is wrong. For every failing
assertion, work out the correct expected value from the SPEC step by step before deciding. Do not use any tools.

SPEC:
{ctx.spec}

CANDIDATE CODE:
{fmt_files({p: v for p, v in c.files.items()})}

HIDDEN TESTS ({ctx.hidden_path}):
```python
{ctx.hidden_tests}```

FAILURE OUTPUT:
```
{clip(out, 4000, tail=True)}
```

If any failing hidden test contradicts the spec, reply:
<verdict>tests</verdict>
<why>one or two sentences</why>
<fixed_hidden_tests>the complete corrected hidden test file (fix or delete only the wrong tests)</fixed_hidden_tests>

If the hidden tests are right and the code is wrong, reply:
<verdict>code</verdict>
<why>one or two sentences</why>
<hint>under 80 words for the developer: the bug and the input class it fails on, without quoting the hidden tests</hint>"""
    reply = ask_claude(prompt, args, f"dispute_r{rnd}_{c.id}")
    verdict = (tag(reply, "verdict") or "").strip().lower()
    why = tag(reply, "why") or ""
    fixed = tag(reply, "fixed_hidden_tests") or ""
    if verdict.startswith("test") and "def test" in fixed:
        ctx.hidden_tests = strip_fences(fixed)
        (args.run_dir / f"hidden_tests_fixed_r{rnd}.py.txt").write_text(ctx.hidden_tests)
        log(f"  dispute on {c.id}: the hidden tests were wrong ({why}) Tests corrected.")
        return "tests"
    hint = tag(reply, "hint") or why
    c.feedback = ("Your code passes the visible tests but fails additional hidden checks of the same spec. "
                  f"A reviewer looked at the failures: {hint}")
    log(f"  dispute on {c.id}: the code is wrong ({why})")
    return "code"


def claude_judge(ctx, finalists: list[Candidate], args) -> tuple[Candidate | None, str]:
    blocks = "\n\n".join(f"CANDIDATE {i + 1}:\n```diff\n{c.diff}```" for i, c in enumerate(finalists))
    prompt = f"""You are reviewing code written by small local models. Do not use any tools.
Every candidate below passes the visible and hidden tests. Pick the one you would merge, judging:
correctness beyond the tests, edge cases, no special-casing of tests, readability, no needless changes.

TASK:
{ctx.task}

SPEC:
{ctx.spec}

{blocks}

Reply exactly as:
<winner>candidate number, or none if none is acceptable</winner>
<reason>two or three sentences</reason>
<fixes>optional: specific problems the winner still has (or, if none is acceptable, what must change)</fixes>"""
    out = ask_claude(prompt, args, f"judge_{Usage.claude_calls}")
    w, reason, fixes = tag(out, "winner") or "", tag(out, "reason") or "", tag(out, "fixes") or ""
    log(f"Claude's verdict: {w} - {reason}")
    if fixes and fixes.lower() not in ("none", "n/a", ""):
        log(f"Claude's notes: {fixes}")
    m = re.search(r"\d+", w)
    if not m or not (1 <= int(m.group()) <= len(finalists)):
        return None, f"{reason} {fixes}".strip()
    return finalists[int(m.group()) - 1], ""


# ----------------------------------------------------------------------------- selection

def other_model(current: str, args) -> str:
    others = [m for m in args.models if m != current]
    return others[0] if others else current


def pick_crossover(alive: list[Thread]):
    """The fittest thread, paired with the thread that passes the most tests it fails."""
    have = [t for t in alive if t.best and t.best.passed_tests and not t.best.note.startswith(("gen", "no-"))]
    if len(have) < 2:
        return None
    a = max(have, key=lambda t: t.fitness())
    if a.best.ok:
        return None
    b = max((t for t in have if t is not a), key=lambda t: len(t.best.passed_tests - a.best.passed_tests))
    return (a, b) if b.best.passed_tests - a.best.passed_tests else None


def select(alive: list[Thread], pop: list[Candidate], rnd: int) -> None:
    for t in alive:
        kids = [c for c in pop if c.thread == t.id]
        if not kids:
            continue
        before = t.best.progress() if t.best else (-1.0, 0)
        t.best = max(kids + ([t.best] if t.best else []), key=lambda c: c.score())
        t.stale = 0 if t.best.progress() > before else t.stale + 1
        t.history.append(f"{t.best.passed}/{t.best.total}")


def near_miss(t: Thread, args) -> bool:
    """A thread whose best attempt is 1-2 failing tests away from passing and has stopped improving."""
    b = t.best
    return (t.alive and b is not None and b.total > 2 and 0 < b.total - b.passed <= args.near_miss
            and b.note in ("", "hidden") and t.stale >= 2)


def prune_duplicates(alive: list[Thread], rnd: int) -> None:
    seen = {}
    for t in sorted(alive, key=lambda t: t.fitness(), reverse=True):
        if not t.best or t.best.note in ("gen-error", "no-files"):
            continue
        if t.origin.startswith("fork") and rnd - t.born < 2:
            continue  # a fresh fork starts as a copy on purpose; give its new model a round first
        key = hashlib.sha1(json.dumps(t.best.files, sort_keys=True).encode()).hexdigest()
        if key in seen:
            t.alive, t.fate = False, f"r{rnd}: same code as {seen[key]}"
            log(f"  {t.id} dropped: identical to {seen[key]}")
        else:
            seen[key] = t.id


def prune_stale(alive: list[Thread], args, rnd: int) -> None:
    leader = max(alive, key=lambda t: t.fitness())
    for t in alive:
        if t is not leader and t.alive and t.stale >= args.patience:
            t.alive, t.fate = False, f"r{rnd}: no progress for {t.stale} rounds"
            log(f"  {t.id} ({t.model}) pruned: no progress for {t.stale} rounds")


# ----------------------------------------------------------------------------- reporting

class Ctx:
    pass


def print_round(rnd: int, threads: list[Thread], pop: list[Candidate]) -> None:
    log(f"Round {rnd} results:")
    for c in sorted(pop, key=lambda c: c.score(), reverse=True):
        extra = f" [{c.note}]" if c.note else ""
        print(f"         {c.id:<6} {c.thread:<4} {c.model:<24} {c.kind:<6} parent={c.parent:<10} "
              f"tests {c.passed}/{c.total}  changed_lines={changed_lines(c.diff)}{extra}")
    log("Threads:")
    for t in threads:
        if t.alive:
            print(f"         {t.id:<4} {t.model:<24} {' -> '.join(t.history[-6:]):<30} stale={t.stale}"
                  + ("  (hinted)" if t.hint else ""))


def save_threads(threads: list[Thread], args) -> None:
    rows = [{"id": t.id, "model": t.model, "origin": t.origin, "born": t.born, "alive": t.alive,
             "fate": t.fate, "history": t.history, "hint": t.hint,
             "best": t.best.id if t.best else None} for t in threads]
    (args.run_dir / "threads.json").write_text(json.dumps(rows, indent=2))


def model_scoreboard(everyone: list[Candidate], winner: Candidate | None, args) -> None:
    log("Per-model results:")
    for m in args.models:
        cs = [c for c in everyone if c.model == m]
        if not cs:
            continue
        best = max(cs, key=lambda c: c.score())
        bad = sum(1 for c in cs if c.note in ("gen-error", "no-files", "syntax"))
        print(f"         {m:<24} {len(cs):>3} candidates  best {best.passed}/{best.total}  "
              f"malformed {bad}" + ("  <- winner" if winner and winner.model == m else ""))


# ----------------------------------------------------------------------------- main loop

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", help="what you want done, in plain English")
    ap.add_argument("--files", nargs="+", required=True, help="files the local models may edit (keep them small)")
    ap.add_argument("--context", nargs="*", default=[], help="read-only files to show as context")
    ap.add_argument("--tests", help="use your own pytest file instead of asking Claude to write tests")
    ap.add_argument("--models", default=",".join(CFG["models"]),
                    help=f"comma-separated Ollama models, assigned round-robin (profile {CFG['profile']})")
    ap.add_argument("--threads", type=int, default=CFG["threads"], help="live threads (lineages) per round")
    ap.add_argument("--max-threads", type=int, default=CFG["threads"] + 2, help="cap on live threads, including Claude's forks")
    ap.add_argument("--children", type=int, default=1, help="children per thread per round")
    ap.add_argument("--no-crossover", action="store_true", help="don't merge threads that pass complementary tests")
    ap.add_argument("--rounds", type=int, default=8, help="maximum rounds")
    ap.add_argument("--patience", type=int, default=2, help="rounds without progress before a thread is pruned")
    ap.add_argument("--review-every", type=int, default=2, help="Claude reviews the threads every N rounds (0 = never)")
    ap.add_argument("--disputes", type=int, default=2,
                    help="times per run Claude may referee code that passes visible but fails hidden tests (0 = off)")
    ap.add_argument("--near-miss", type=int, default=2,
                    help="a thread this many failing tests from passing, stuck 2+ rounds, gets an early review and "
                         "may receive a code snippet from Claude (0 = off)")
    ap.add_argument("--claude-budget", type=int, default=6, help="max Claude calls per run (plan + reviews + judge)")
    ap.add_argument("--review-diff-chars", type=int, default=2500, help="diff shown to Claude per thread")
    ap.add_argument("--review-fail-chars", type=int, default=600, help="failure output shown to Claude per thread")
    ap.add_argument("--parallel", type=int, default=CFG["parallel"], help="concurrent generations per model")
    ap.add_argument("--ctx", type=int, default=CFG["ctx"], help="context window per generation")
    ap.add_argument("--max-tokens", type=int, default=6144, help="max tokens a local model may write")
    ap.add_argument("--local-timeout", type=int, default=900, help="seconds per local generation")
    ap.add_argument("--test-timeout", type=int, default=120, help="seconds per test run")
    ap.add_argument("--full-suite", action="store_true", help="finalists must also pass your whole test suite")
    ap.add_argument("--always-judge", action="store_true", help="have Claude review even a single finalist")
    ap.add_argument("--no-claude", action="store_true", help="never call Claude (requires --tests)")
    ap.add_argument("--claude-model", help="e.g. sonnet or opus (default: your Claude Code default)")
    ap.add_argument("--allow-dirty", action="store_true", help="run even with uncommitted changes")
    ap.add_argument("--summary-json", help="also write a machine-readable run summary to this path")
    args = ap.parse_args()

    args.models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not args.models:
        die("--models is empty")
    if args.no_claude and not args.tests:
        die("--no-claude needs --tests (someone has to write the tests)")
    args.max_threads = max(args.max_threads, args.threads)

    top = run(["git", "rev-parse", "--show-toplevel"])
    if top.returncode != 0:
        die("run this inside a git repository")
    repo = Path(top.stdout.strip()).resolve()
    orig_cwd = Path.cwd()
    os.chdir(repo)
    if run(["git", "rev-parse", "HEAD"]).returncode != 0:
        die("the repository has no commits yet; make an initial commit first")
    if run(["git", "status", "--porcelain"]).stdout.strip() and not args.allow_dirty:
        die("you have uncommitted changes. Commit or stash them first (candidates are built from HEAD), "
            "or pass --allow-dirty.")
    if run([sys.executable, "-m", "pytest", "--version"]).returncode != 0:
        die(f"pytest isn't installed for {sys.executable}. Run: {sys.executable} -m pip install pytest")
    check_ollama(args)

    ctx = Ctx()
    ctx.task, ctx.hint, ctx.spec = args.task, "", args.task
    ctx.src_layout = (repo / "src").is_dir()

    def rel(p: str) -> str:
        try:
            return (orig_cwd / p).resolve().relative_to(repo).as_posix()
        except ValueError:
            die(f"{p} is outside the repository")

    ctx.original = {}
    for p in args.files:
        f = repo / rel(p)
        ctx.original[rel(p)] = f.read_text() if f.exists() else ""
    ctx.context_files = {rel(p): (repo / rel(p)).read_text() for p in args.context}
    slug = slugify(args.task)
    test_dir = "tests" if (repo / "tests").is_dir() or not (repo / "test").is_dir() else "test"
    ctx.visible_path = f"{test_dir}/test_evolve_{slug}.py"
    ctx.hidden_path = f"{test_dir}/test_evolve_{slug}_hidden.py"
    ctx.hidden_tests = ""

    args.run_dir = Path.home() / ".cache" / "evolve" / repo.name / time.strftime("%Y%m%d-%H%M%S")
    args.run_dir.mkdir(parents=True, exist_ok=True)
    log(f"Run folder (logs, prompts, patches): {args.run_dir}")
    log(f"Models: {', '.join(args.models)}")

    # 1. Plan
    if args.tests:
        ctx.visible_path = rel(args.tests)
        ctx.visible_tests = (repo / ctx.visible_path).read_text()
        log(f"Using your tests: {ctx.visible_path}")
    else:
        listing = "\n".join(run(["git", "ls-files"]).stdout.splitlines()[:300])
        claude_plan(ctx, args, listing)
        log(f"Spec and tests ready ({ctx.visible_tests.count('def test')} visible, "
            f"{ctx.hidden_tests.count('def test')} hidden tests).")
    (args.run_dir / "spec.md").write_text(ctx.spec)
    (args.run_dir / "visible_tests.py.txt").write_text(ctx.visible_tests)
    (args.run_dir / "hidden_tests.py.txt").write_text(ctx.hidden_tests)

    # 2. Threads
    threads: list[Thread] = []
    rr = [0]

    def spawn(model: str | None, origin: str, born: int, hint: str = "") -> Thread:
        if model is None:
            model = args.models[rr[0] % len(args.models)]
            rr[0] += 1
        t = Thread(f"T{len(threads) + 1}", model, born, origin, hint=hint)
        threads.append(t)
        return t

    ctx.spawn = spawn
    for _ in range(args.threads):
        spawn(None, "seed", 1)

    # 3. Worktrees, a pool of test slots
    n_slots = max(1, min(6, args.max_threads * args.children + 1))
    slots = [args.run_dir / "slots" / f"slot{i}" for i in range(n_slots)]
    for s in slots:
        r = run(["git", "worktree", "add", "--detach", "-f", str(s), "HEAD"])
        if r.returncode != 0:
            die(f"git worktree add failed: {r.stderr}")

    winner, everyone, last_model, counter, rounds_run = None, [], None, 0, 0
    disputes_left = args.disputes
    try:
        for rnd in range(1, args.rounds + 1):
            rounds_run = rnd
            alive = [t for t in threads if t.alive]

            # Breed: mutate each thread's fittest attempt (or start fresh), plus one crossover.
            jobs = []
            for i, t in enumerate(alive):
                for k in range(args.children):
                    counter += 1
                    if t.best is None or t.best.note in ("gen-error", "no-files"):
                        temp = 0.2 + 0.7 * ((i * args.children + k) % 4) / 3
                        jobs.append(Job(f"c{counter}", t, None, None, temp))
                    else:
                        temp = min(1.0, 0.35 + 0.15 * k + 0.1 * min(t.stale, 3))
                        jobs.append(Job(f"c{counter}", t, t.best, None, temp))
            pair = None if args.no_crossover else pick_crossover(alive)
            if pair:
                counter += 1
                jobs.append(Job(f"c{counter}", pair[0], pair[0].best, pair[1].best, 0.5))

            # Run the model that's already loaded first, so each round costs one fewer model swap.
            used = {j.thread.model for j in jobs}
            order = sorted(used, key=lambda m: (m != last_model, args.models.index(m)))
            log(f"Round {rnd}: {len(jobs)} candidates across {len(alive)} threads"
                + (f" (crossover {pair[0].id} x {pair[1].id})" if pair else "") + " ...")
            pop = generate_all(jobs, ctx, args, order)
            last_model = order[-1]
            log("Testing ...")
            pop = evaluate_all(pop, slots, ctx, args)
            everyone += pop

            # Hidden-test gate: a visible pass only counts if the hidden tests pass too.
            finalists, disputed_this_round = [], False
            for c in sorted([c for c in pop if c.ok], key=lambda c: c.score(), reverse=True)[:4]:
                ok, out = final_check(c, slots[0], ctx, args)
                if not ok and not disputed_this_round and disputes_left > 0 and ctx.hidden_tests \
                        and not args.full_suite and claude_left(args) > 1:
                    # Referee once per round: were the hidden tests wrong, or the code?
                    disputes_left -= 1
                    disputed_this_round = True
                    (args.run_dir / f"{c.id}_final_check.txt").write_text(out)
                    if claude_dispute(ctx, c, out, args, rnd) == "tests":
                        ok, out = final_check(c, slots[0], ctx, args)
                    else:
                        c.note = "hidden"
                        continue
                if ok:
                    finalists.append(c)
                else:
                    log(f"  {c.id} ({c.thread}) passes visible tests but fails the hidden/full-suite checks.")
                    (args.run_dir / f"{c.id}_final_check.txt").write_text(out)
                    c.note = "hidden"
                    if not c.feedback.startswith("Your code passes the visible tests but fails additional hidden checks"):
                        c.feedback = ("Your code passes the visible tests but fails additional hidden checks of the "
                                      "same spec. Make the implementation fully general: re-read the spec, handle "
                                      "every edge case it lists, and do not special-case test inputs.")

            select(alive, pop, rnd)
            print_round(rnd, threads, pop)

            if finalists:
                if len(finalists) == 1 and not args.always_judge:
                    winner = finalists[0]
                elif claude_left(args) <= 0:
                    winner = finalists[0]
                else:
                    winner, why = claude_judge(ctx, finalists, args)
                    if winner is None:
                        log("Claude rejected all finalists; they go back into the pool with its feedback.")
                        for c in finalists:
                            c.note = "rejected"
                            c.feedback = f"A senior reviewer rejected this version (all tests pass): {why}"
                            (args.run_dir / f"{c.id}.patch").write_text(c.diff)
                if winner:
                    break
            if rnd == args.rounds:
                break

            # Cull: free local pruning every round, Claude's review on schedule.
            alive = [t for t in threads if t.alive]
            prune_duplicates(alive, rnd)
            alive = [t for t in threads if t.alive]
            scheduled = args.review_every and rnd % args.review_every == 0
            stuck_close = args.near_miss and any(near_miss(t, args) for t in alive)
            review_due = (scheduled or stuck_close) and claude_left(args) > 1  # always keep one call for the judge
            if stuck_close and not scheduled and review_due:
                log("  near miss: a thread is 1-2 tests from passing and stuck, asking Claude early")
            if review_due:
                if claude_review(ctx, threads, args, rnd):
                    live = [t.best for t in threads if t.alive and t.best]
                    evaluate_all(live, slots, ctx, args)  # rescore against the corrected tests
            else:
                prune_stale(alive, args, rnd)

            # Refill the population with fresh threads so diversity never collapses.
            while sum(t.alive for t in threads) < args.threads:
                t = spawn(None, "refill", rnd + 1)
                log(f"  new thread {t.id} on {t.model}")
            save_threads(threads, args)
    finally:
        save_threads(threads, args)
        for s in slots:
            run(["git", "worktree", "remove", "--force", str(s)])
        run(["git", "worktree", "prune"])

    # 4. Apply
    print()
    if winner:
        (args.run_dir / "winner.patch").write_text(winner.diff)
        write_files(repo, winner.files)
        tests = {ctx.visible_path: ctx.visible_tests}
        if ctx.hidden_tests:
            tests[ctx.hidden_path] = ctx.hidden_tests
        if not args.tests:
            write_files(repo, tests)
        log(f"Applied {winner.id} from thread {winner.thread} ({winner.model}, {changed_lines(winner.diff)} "
            f"changed lines) to your working tree" + ("" if args.tests else f", plus tests in {test_dir}/") + ".")
        new_files = [p for p in {**winner.files, **({} if args.tests else tests)} if not ctx.original.get(p)]
        undo = "git checkout -- " + " ".join(p for p in winner.files if ctx.original.get(p))
        if new_files:
            undo += " ; rm " + " ".join(new_files)
        log("Review it with `git diff` and `git status`.")
        log(f"To undo: {undo}")
    else:
        best = max(everyone, key=lambda c: c.score()) if everyone else None
        if best:
            (args.run_dir / "best_attempt.patch").write_text(best.diff)
            log(f"No candidate passed. Best attempt {best.id} ({best.model}, {best.passed}/{best.total}) saved to "
                f"{args.run_dir / 'best_attempt.patch'}. Nothing was changed in your repo.")
            log("Next step: hand the task to Claude Code directly, or split it into smaller pieces.")

    model_scoreboard(everyone, winner, args)
    log(f"Usage: {Usage.local_calls} local generations, {Usage.claude_calls} Claude calls.")
    log(f"🔴 Claude: {Usage.claude_new + Usage.claude_cached:,} tokens ({Usage.claude_new:,} new · "
        f"{Usage.claude_cached:,} re-read from cache · {Usage.claude_output:,} written), ${Usage.claude_cost:.3f} at API prices")
    log(f"🟢 Local models: {Usage.local_tokens:,} tokens ({Usage.local_output:,} written), not billed to Claude")
    if args.summary_json:
        Path(args.summary_json).write_text(json.dumps({
            "solved": bool(winner), "winner_model": winner.model if winner else None,
            "winner_lines": changed_lines(winner.diff) if winner else 0, "rounds": rounds_run,
            "seconds": round(time.time() - T0, 1), "claude_calls": Usage.claude_calls, "disputes_used": args.disputes - disputes_left,
            "claude_new": Usage.claude_new, "claude_cached": Usage.claude_cached,
            "claude_output": Usage.claude_output, "claude_cost_usd": round(Usage.claude_cost, 4),
            "local_calls": Usage.local_calls, "local_tokens": Usage.local_tokens,
            "local_output": Usage.local_output, "run_dir": str(args.run_dir)}, indent=2))
    sys.exit(0 if winner else 1)


if __name__ == "__main__":
    main()
