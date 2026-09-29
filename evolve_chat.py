#!/usr/bin/env python3
"""
evolve_chat.py - Darwinian tournament for chat-style tasks, run entirely on local models.

    task + rubric (written by Claude)
      -> N candidate answers, dealt round-robin across the local model roster
      -> each round: Swiss-paired duels judged by a local model (both orders, to cancel position bias)
                     top half survives; each survivor is revised using the critiques it received
      -> final round-robin among the leaders
      -> the top few answers go back to Claude, which picks or polishes one

Used by mcp_server.py (Claude desktop app: Chat / Cowork), or directly from a terminal:

    python evolve_chat.py "Write a 150-word cover letter opening for ..." --rubric "specific, no cliches"

Needs Ollama running (python3 start_ollama.py). Standard library only.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_URL = _host if _host.startswith("http") else f"http://{_host}"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hardware  # noqa: E402

CFG = hardware.load_config()      # this machine's profile; start_ollama.py serves with the same values
CTX, PARALLEL = CFG["ctx"], CFG["parallel"]
LOG_ROOT = Path.home() / ".cache" / "evolve" / "chat"

# Best first. General models write and judge prose better than coder models; any installed model
# not listed here is appended after these.
PREFERRED = ["qwen3:14b", "gemma3:12b", "qwen2.5:14b", "mistral-nemo:12b", "llama3.1:8b",
             "qwen2.5-coder:14b", "deepseek-coder-v2:16b", "qwen2.5-coder:7b"]

WRITER_SYSTEM = """You are a skilled writer and analyst. Produce the best possible response to the task.
Follow the rubric closely. Be accurate: if you are not sure of a fact, say so rather than inventing it.
Output only the response itself: no preamble, no notes about what you did."""

JUDGE_SYSTEM = """You are a strict, fair reviewer comparing two responses to the same task.
Judge only against the task and the rubric. Accuracy and following instructions matter most.
Do NOT prefer a response for being longer, more confident, or more elaborately formatted.
Reply with JSON only."""

_last_model = [None]


# ----------------------------------------------------------------------------- ollama

class OllamaDown(RuntimeError):
    pass


LEDGER = Path.home() / ".cache" / "evolve" / "ledger.jsonl"


def record_local(model: str, data: dict, source: str) -> None:
    """Append Ollama's exact token counts to the ledger read by token_footer.py."""
    row = {"ts": time.time(), "model": model, "source": source,
           "in": data.get("prompt_eval_count", 0), "out": data.get("eval_count", 0)}
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "a") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass


def local_tokens_since(ts: float) -> int:
    total = 0
    try:
        for line in LEDGER.read_text().splitlines():
            r = json.loads(line)
            if r["ts"] >= ts:
                total += r["in"] + r["out"]
    except (OSError, ValueError, KeyError):
        pass
    return total


def installed_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
            names = [m["name"] for m in json.load(resp).get("models", [])]
    except (urllib.error.URLError, OSError) as e:
        raise OllamaDown(f"can't reach Ollama at {OLLAMA_URL} ({e}). Start it with `python3 start_ollama.py`") from e
    return [n for n in names if "embed" not in n]


def roster() -> list[str]:
    have = installed_models()
    env = [m.strip() for m in os.environ.get("EVOLVE_CHAT_MODELS", "").split(",") if m.strip()]
    if env:
        missing = [m for m in env if m not in have]
        if missing:
            raise OllamaDown(f"not pulled: {', '.join(missing)}. Run: ollama pull {missing[0]}")
        return env
    order = PREFERRED + [m for m in CFG["models"] if m not in PREFERRED]
    ranked = [m for m in order if m in have] + sorted(m for m in have if m not in order)
    if not ranked:
        raise OllamaDown(f"no models pulled. Run: python3 install.py (or ollama pull {CFG['models'][0]})")
    return ranked[:3]


def judge_model(models: list[str]) -> str:
    return os.environ.get("EVOLVE_CHAT_JUDGE") or models[0]


def chat(model: str, system: str, user: str, temperature: float, max_tokens: int,
         json_mode: bool = False, timeout: int = 900) -> str:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": temperature, "num_ctx": CTX, "num_predict": max_tokens},
    }
    if json_mode:
        body["format"] = "json"
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, OSError) as e:
        raise OllamaDown(f"Ollama request failed ({e})") from e
    record_local(model, data, "chat")
    text = data.get("message", {}).get("content", "")
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def run_grouped(jobs: list[tuple[str, callable]]) -> list:
    """jobs: (model, thunk). One model at a time (only one fits in memory), its jobs in parallel slots.
    The model that's already loaded goes first. Results come back in the original order."""
    results = [None] * len(jobs)
    models = []
    for m, _ in jobs:
        if m not in models:
            models.append(m)
    models.sort(key=lambda m: m != _last_model[0])
    for m in models:
        idx = [i for i, (jm, _) in enumerate(jobs) if jm == m]
        with cf.ThreadPoolExecutor(min(len(idx), PARALLEL)) as ex:
            for i, r in zip(idx, ex.map(lambda i: jobs[i][1](), idx)):
                results[i] = r
        _last_model[0] = m
    return results


# ----------------------------------------------------------------------------- tournament

@dataclass
class Entry:
    id: str
    model: str
    text: str
    parent: str = "-"
    wins: float = 0.0
    games: int = 0
    critiques: list = field(default_factory=list)

    def rate(self) -> float:
        # Unplayed entries sit in the middle so they get paired against contenders.
        return self.wins / self.games if self.games else 0.5


def task_block(task: str, rubric: str, context: str) -> str:
    parts = [f"TASK:\n{task}"]
    if context:
        parts.append(f"CONTEXT / SOURCE MATERIAL:\n{context}")
    parts.append(f"RUBRIC (what a great response does):\n{rubric or 'Accurate, complete, clear, concise.'}")
    return "\n\n".join(parts)


def duel(tb: str, a: Entry, b: Entry, judge: str) -> tuple[float, str, str]:
    """Returns (a's score in [0, 1], critique of a, critique of b). Judged in both orders."""
    score, crit_a, crit_b = 0.0, [], []
    for first, second, a_is_first in ((a, b, True), (b, a, False)):
        prompt = (f"{tb}\n\nRESPONSE A:\n<<<\n{first.text}\n>>>\n\nRESPONSE B:\n<<<\n{second.text}\n>>>\n\n"
                  'Reply as JSON: {"better": "A" or "B" or "tie", '
                  '"critique_A": "the single most important fix for A, under 40 words", '
                  '"critique_B": "the single most important fix for B, under 40 words"}')
        try:
            raw = chat(judge, JUDGE_SYSTEM, prompt, 0.1, 300, json_mode=True)
            v = json.loads(raw)
        except (json.JSONDecodeError, OllamaDown):
            score += 0.5
            continue
        better = str(v.get("better", "tie")).strip().upper()[:1]
        if better == ("A" if a_is_first else "B"):
            score += 1
        elif better not in ("A", "B"):
            score += 0.5
        ca, cb = (str(v.get(k, "")).strip() for k in ("critique_A", "critique_B"))
        ca, cb = ("" if re.match(r"(none|n/?a)\b", c, re.I) else c for c in (ca, cb))
        (crit_a if a_is_first else crit_b).append(ca)
        (crit_b if a_is_first else crit_a).append(cb)
    return score / 2, " / ".join(c for c in crit_a if c), " / ".join(c for c in crit_b if c)


def play(pairs: list[tuple[Entry, Entry]], tb: str, judge: str) -> None:
    results = run_grouped([(judge, lambda p=p: duel(tb, p[0], p[1], judge)) for p in pairs])
    for (a, b), (sa, ca, cb) in zip(pairs, results):
        a.wins += sa
        b.wins += 1 - sa
        a.games += 1
        b.games += 1
        if ca:
            a.critiques.append(ca)
        if cb:
            b.critiques.append(cb)


def swiss_pairs(pop: list[Entry]) -> list[tuple[Entry, Entry]]:
    ranked = sorted(pop, key=lambda e: (e.rate(), random.random()), reverse=True)
    return [(ranked[i], ranked[i + 1]) for i in range(0, len(ranked) - 1, 2)]


def evolve(task: str, rubric: str = "", context: str = "", n: int = 6, rounds: int = 2,
           finalists: int = 2, max_tokens: int = 1500, models: list[str] | None = None,
           judge: str | None = None, progress=print) -> dict:
    t0 = time.time()
    models = models or roster()
    judge = judge or judge_model(models)
    n = max(2, min(n, 12))
    tb = task_block(task, rubric, context)
    log_dir = LOG_ROOT / time.strftime("%Y%m%d-%H%M%S")
    log_dir.mkdir(parents=True, exist_ok=True)
    calls = [0]

    def write(model: str, temp: float, user: str) -> str:
        calls[0] += 1
        return chat(model, WRITER_SYSTEM, user, temp, max_tokens)

    # Seed: diverse models and temperatures.
    progress(f"writing {n} candidates with {', '.join(models)}")
    specs = [(models[i % len(models)], 0.3 + 0.7 * i / max(1, n - 1)) for i in range(n)]
    texts = run_grouped([(m, lambda m=m, t=t: write(m, t, tb)) for m, t in specs])
    pop = [Entry(f"e{i + 1}", m, txt) for i, ((m, _), txt) in enumerate(zip(specs, texts)) if txt]
    if len(pop) < 2:
        raise RuntimeError("local models produced fewer than 2 usable answers")
    counter = len(pop)

    for r in range(1, rounds + 1):
        progress(f"round {r}/{rounds}: judging {len(pop) // 2} duels with {judge}")
        play(swiss_pairs(pop), tb, judge)
        calls[0] += 2 * (len(pop) // 2)
        survivors = sorted(pop, key=lambda e: e.rate(), reverse=True)[:math.ceil(len(pop) / 2)]
        progress(f"round {r}/{rounds}: revising {len(survivors)} survivors")

        def revise(e: Entry) -> str:
            notes = "\n".join(f"- {c}" for c in e.critiques[-3:]) or "- Make it tighter and more specific."
            return write(e.model, 0.5, f"{tb}\n\nYOUR DRAFT:\n<<<\n{e.text}\n>>>\n\nREVIEWER CRITIQUES:\n{notes}\n\n"
                                       "Rewrite the draft to fix these problems while keeping what is good. "
                                       "Output only the improved response.")

        new = run_grouped([(e.model, lambda e=e: revise(e)) for e in survivors])
        children = []
        for e, txt in zip(survivors, new):
            if txt:
                counter += 1
                children.append(Entry(f"e{counter}", e.model, txt, parent=e.id))
        pop = survivors + children

    # Final: round-robin among the leaders (children haven't played yet, so everyone gets games here).
    top = sorted(pop, key=lambda e: e.rate(), reverse=True)[:max(3, min(4, finalists + 1))]
    for e in top:
        e.wins, e.games = 0.0, 0
    pairs = [(top[i], top[j]) for i in range(len(top)) for j in range(i + 1, len(top))]
    progress(f"final: round-robin of {len(top)} leaders ({len(pairs)} duels)")
    play(pairs, tb, judge)
    calls[0] += 2 * len(pairs)
    final = sorted(top, key=lambda e: e.rate(), reverse=True)[:finalists]

    result = {
        "finalists": [{"id": e.id, "model": e.model, "parent": e.parent,
                       "record": f"{e.wins:g}/{e.games}", "critiques": e.critiques[-2:], "text": e.text}
                      for e in final],
        "models": models, "judge": judge, "local_calls": calls[0],
        "seconds": round(time.time() - t0), "log_dir": str(log_dir),
    }
    (log_dir / "result.json").write_text(json.dumps({"task": task, "rubric": rubric, **result}, indent=2))
    (log_dir / "all_entries.json").write_text(json.dumps(
        [{"id": e.id, "model": e.model, "parent": e.parent, "wins": e.wins, "games": e.games,
          "critiques": e.critiques, "text": e.text} for e in pop], indent=2))
    return result


def draft(prompt: str, n: int = 1, system: str = "", max_tokens: int = 2000,
          models: list[str] | None = None, progress=print) -> dict:
    """Plain bulk generation: n independent drafts, no judging."""
    t0 = time.time()
    models = models or roster()
    n = max(1, min(n, 8))
    progress(f"drafting {n} with {', '.join(models[:n])}")
    specs = [(models[i % len(models)], 0.4 + 0.5 * i / max(1, n - 1)) for i in range(n)]
    texts = run_grouped([(m, lambda m=m, t=t: chat(m, system or WRITER_SYSTEM, prompt, t, max_tokens))
                         for m, t in specs])
    return {"drafts": [{"model": m, "text": t} for (m, _), t in zip(specs, texts)],
            "seconds": round(time.time() - t0)}


def format_evolve(res: dict) -> str:
    out = [f"Local tournament finished in {res['seconds']}s: {res['local_calls']} local model calls, "
           f"writers {', '.join(res['models'])}, judge {res['judge']}. Logs: {res['log_dir']}", ""]
    for i, f in enumerate(res["finalists"], 1):
        crit = "; ".join(c for c in f["critiques"] if c) or "-"
        out += [f"=== FINALIST {i}  ({f['model']}, final round score {f['record']}, "
                f"{'revision of ' + f['parent'] if f['parent'] != '-' else 'original draft'})",
                f"remaining critiques: {crit}", "", f["text"], ""]
    out.append("These were written and ranked by small local models. Check facts, pick the best "
               "(or merge them), and fix the remaining critiques before presenting it.")
    return "\n".join(out)


def format_draft(res: dict) -> str:
    out = [f"{len(res['drafts'])} local draft(s) in {res['seconds']}s.", ""]
    for i, d in enumerate(res["drafts"], 1):
        out += [f"=== DRAFT {i}  ({d['model']})", "", d["text"], ""]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task")
    ap.add_argument("--rubric", default="")
    ap.add_argument("--context-file", help="text file with source material")
    ap.add_argument("-n", type=int, default=6, help="candidates")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--finalists", type=int, default=2)
    ap.add_argument("--max-tokens", type=int, default=1500)
    a = ap.parse_args()
    ctx = Path(a.context_file).read_text() if a.context_file else ""
    res = evolve(a.task, a.rubric, ctx, a.n, a.rounds, a.finalists, a.max_tokens,
                 progress=lambda m: print(f"[evolve_chat] {m}", flush=True))
    print(format_evolve(res))


if __name__ == "__main__":
    main()
