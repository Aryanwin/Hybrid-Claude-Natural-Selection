#!/usr/bin/env python3
"""
mcp_server.py - exposes the local-model tournament (evolve_chat.py) to the Claude desktop app as MCP tools,
so Claude in Chat / Cowork can hand bulky generation to free local models and only read the finalists.

Tools:
    local_evolve   start a tournament (task + rubric) and wait up to wait_seconds for the finalists
    local_draft    n plain drafts from local models, no judging
    local_result   keep waiting for a job that was still running
    local_models   is Ollama up, which models will be used

Registered by register_mcp.py: in the Claude desktop app (Chat, Cowork) with --preset chat, and in Claude Code
as "local-evolve-code" with --preset code.
Speaks MCP over stdio (newline-delimited JSON-RPC 2.0). Standard library only. Logs go to stderr.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evolve_chat as ec  # noqa: E402

SERVER_INFO = {"name": "local-evolve", "version": "1.1.0"}

# Presets, chosen per registration with --preset (see register_mcp.py):
#   chat  Claude desktop app (Chat, Cowork): smaller tournaments that finish in ~1-2 tool calls (~45-60 s),
#         because Chat tends to answer by itself instead of polling a long-running job
#   code  Claude Code: the full tournament; Claude Code polls local_result reliably
PRESETS = {"chat": {"candidates": 4, "rounds": 1}, "code": {"candidates": 6, "rounds": 2}}
PRESET_NAME = sys.argv[sys.argv.index("--preset") + 1] if "--preset" in sys.argv else "chat"
if PRESET_NAME not in PRESETS:
    sys.exit(f"unknown --preset {PRESET_NAME!r}; use one of {', '.join(PRESETS)}")
PRESET = PRESETS[PRESET_NAME]

INSTRUCTIONS = """Free local models (Ollama on the user's computer) you can hand bulky generation to, to save Claude usage.
Use local_evolve when the user wants something long or many options where quality can be judged against a
rubric: drafts of essays/letters/reports/study notes, rewriting or summarizing long pasted material,
brainstorming many names/ideas/angles. Write a short, concrete rubric; pass source material as context.
You get back the top 2 answers from a local tournament: pick or merge the best, check facts (small models
hallucinate), fix the remaining critiques, and present the result as your answer.
Do NOT use it for quick questions, facts or current events, math you can do directly, code in a repo
(evolve.py covers that), or anything the user wants from Claude specifically. If the tools report Ollama is
offline, just answer normally.
A tournament takes about a minute, longer than one tool call can wait. When a call returns "STILL RUNNING" with a
job_id, call local_result with that job_id, and again if it is still running, until you get "RESULT READY".
Do not write your own answer while a job is running: the local models are already writing it.
After a reply in which you used these tools, end it with exactly two lines:
🔴 Claude: ≈<estimate> tokens (estimate: you cannot see your exact usage; count the tool results you read plus
the text you wrote, ÷4 characters per token, and say "estimate")
🟢 Local models: <sum of LOCAL_TOKENS from this reply's tool results> tokens (exact)"""

TOOLS = [
    {
        "name": "local_evolve",
        "description": "Run a Darwinian tournament on the user's local models: several drafts, judged in "
                       "pairwise duels by a local model, the best revised from critiques, repeated. Returns "
                       "the top finalists. Takes 2-8 minutes; returns a job_id if not done within wait_seconds (then call local_result).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Complete, self-contained instructions for the writers."},
                "rubric": {"type": "string", "description": "What a great answer does: 3-6 concrete criteria "
                                                            "(length, tone, must-include points, what to avoid)."},
                "context": {"type": "string", "description": "Source material the answer must be based on."},
                "candidates": {"type": "integer", "default": PRESET["candidates"], "minimum": 2, "maximum": 12},
                "rounds": {"type": "integer", "default": PRESET["rounds"], "minimum": 0, "maximum": 4},
                "finalists": {"type": "integer", "default": 2, "minimum": 1, "maximum": 3},
                "max_tokens": {"type": "integer", "default": 1500, "description": "Max length of each answer."},
                "wait_seconds": {"type": "integer", "default": 40, "maximum": 45},
            },
            "required": ["task"],
        },
    },
    {
        "name": "local_draft",
        "description": "Generate n independent drafts with the user's local models (no judging). Good for "
                       "cheap raw material: first drafts, many variations, bulk rewriting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "n": {"type": "integer", "default": 1, "minimum": 1, "maximum": 8},
                "system": {"type": "string", "description": "Optional system prompt for the local models."},
                "max_tokens": {"type": "integer", "default": 2000},
                "wait_seconds": {"type": "integer", "default": 40, "maximum": 45},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "local_result",
        "description": "Wait for a local_evolve / local_draft job that was still running, and return its result.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "wait_seconds": {"type": "integer", "default": 40, "maximum": 45},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "local_models",
        "description": "Check whether the local models are online and which ones will write and judge.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# ----------------------------------------------------------------------------- jobs

class Job:
    def __init__(self, kind: str):
        self.id = uuid.uuid4().hex[:8]
        self.kind = kind
        self.started = time.time()
        self.done = threading.Event()
        self.progress = "starting"
        self.text = ""
        self.error = ""


JOBS: dict[str, Job] = {}
RUN_LOCK = threading.Lock()  # one tournament at a time: they share the same GPU


def start(kind: str, fn, *a, **kw) -> Job:
    job = Job(kind)
    JOBS[job.id] = job

    def target():
        try:
            with RUN_LOCK:
                t0 = time.time()
                job.text = fn(*a, progress=lambda m: setattr(job, "progress", m), **kw)
                n = ec.local_tokens_since(t0)
                job.text += (f"\n\nLOCAL_TOKENS={n}  (exact count from Ollama; tokens handled on the user's computer "
                             f"instead of by Claude)")
        except ec.OllamaDown as e:
            job.error = f"Local models are offline: {e}. Answer the user directly instead."
        except Exception as e:  # report, don't crash the server
            job.error = f"{type(e).__name__}: {e}"
            log(traceback.format_exc())
        finally:
            job.done.set()

    threading.Thread(target=target, daemon=True).start()
    return job


def wait(job: Job, seconds) -> tuple[str, bool]:
    seconds = max(1, min(int(seconds or 40), 45))
    job.done.wait(seconds)
    if not job.done.is_set():
        el = int(time.time() - job.started)
        return (f"STILL RUNNING after {el}s ({job.progress}). job_id={job.id}. "
                f"Call local_result with job_id={job.id} now to keep waiting; don't answer the user yourself yet."), False
    if job.error:
        return job.error, True
    return f"RESULT READY\n\n{job.text}", False


def call_tool(name: str, args: dict) -> tuple[str, bool]:
    if name == "local_models":
        try:
            models = ec.roster()
        except ec.OllamaDown as e:
            return f"Offline: {e}", True
        return (f"Online. Writers: {', '.join(models)}. Judge: {ec.judge_model(models)}. "
                f"Context {ec.CTX} tokens, {ec.PARALLEL} parallel slots. Preset '{PRESET_NAME}': "
                f"{PRESET['candidates']} drafts, {PRESET['rounds']} revision round(s) per tournament."), False
    if name == "local_result":
        job = JOBS.get(str(args.get("job_id", "")))
        if not job:
            return "Unknown job_id (the server may have restarted). Start the task again.", True
        return wait(job, args.get("wait_seconds"))
    if name == "local_evolve":
        if not str(args.get("task", "")).strip():
            return "task is required", True

        def run(progress):
            return ec.format_evolve(ec.evolve(
                args["task"], args.get("rubric", ""), args.get("context", ""),
                int(args.get("candidates", PRESET["candidates"])), int(args.get("rounds", PRESET["rounds"])),
                int(args.get("finalists", 2)),
                int(args.get("max_tokens", 1500)), progress=progress))

        return wait(start("evolve", lambda progress: run(progress)), args.get("wait_seconds"))
    if name == "local_draft":
        if not str(args.get("prompt", "")).strip():
            return "prompt is required", True

        def run(progress):
            return ec.format_draft(ec.draft(args["prompt"], int(args.get("n", 1)), args.get("system", ""),
                                            int(args.get("max_tokens", 2000)), progress=progress))

        return wait(start("draft", lambda progress: run(progress)), args.get("wait_seconds"))
    return f"Unknown tool: {name}", True


# ----------------------------------------------------------------------------- JSON-RPC over stdio

OUT_LOCK = threading.Lock()


def log(msg: str) -> None:
    print(f"[local-evolve] {msg}", file=sys.stderr, flush=True)


def send(obj: dict) -> None:
    with OUT_LOCK:
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()


def handle(msg: dict) -> None:
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:  # notification (initialized, cancelled, ...)
        return
    try:
        if method == "initialize":
            result = {"protocolVersion": params.get("protocolVersion", "2025-06-18"),
                      "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO, "instructions": INSTRUCTIONS}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            text, is_error = call_tool(params.get("name", ""), params.get("arguments") or {})
            result = {"content": [{"type": "text", "text": text}], "isError": is_error}
        elif method == "ping":
            result = {}
        elif method in ("resources/list", "prompts/list"):
            result = {method.split("/")[0]: []}
        else:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"unknown method {method}"}})
            return
        send({"jsonrpc": "2.0", "id": mid, "result": result})
    except Exception as e:
        log(traceback.format_exc())
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}})


def main() -> None:
    log("started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log(f"bad JSON: {line[:200]}")
            continue
        # Tool calls can block for up to ~45s, so each request gets its own thread.
        threading.Thread(target=handle, args=(msg,), daemon=True).start()


if __name__ == "__main__":
    main()
