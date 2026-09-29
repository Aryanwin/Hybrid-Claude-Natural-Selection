#!/usr/bin/env python3
"""
token_footer.py - Claude Code Stop hook: after every response, show how many Claude tokens the turn used
and how many tokens local models handled instead.

    🔴 Claude: 184,203 tokens this turn (3,412 new · 180,791 re-read from cache)
    🟢 Local models: 12,880 tokens handled on this machine, not billed to Claude

Claude numbers are exact: summed from the `usage` block of every API call in the session transcript
since your last message. Local numbers are exact too: Ollama's token counts, logged by evolve.py /
evolve_chat.py / the local-evolve MCP server to ~/.cache/evolve/ledger.jsonl.

Registered in ~/.claude/settings.json as a Stop hook. Standard library only; never fails the turn.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

LEDGER = Path.home() / ".cache" / "evolve" / "ledger.jsonl"


def is_prompt(d: dict) -> bool:
    """A message you typed (not a tool result, not injected skill/system text)."""
    if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
        return False
    c = (d.get("message") or {}).get("content")
    if isinstance(c, str):
        return not c.startswith("<")  # skips <command-...>, <local-command-...> wrappers
    return isinstance(c, list) and any(b.get("type") == "text" for b in c) \
        and not any(b.get("type") == "tool_result" for b in c)


def ts(d: dict) -> float:
    try:
        return datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError):
        return 0.0


def main() -> None:
    try:
        hook = json.load(sys.stdin)
        rows = []
        with open(hook["transcript_path"]) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        return

    start = max((i for i, d in enumerate(rows) if is_prompt(d)), default=0)
    turn_start = ts(rows[start]) if rows else 0.0

    # One API call can be written as several transcript lines (thinking, text, tool_use): count each id once.
    seen, new, cached, out = set(), 0, 0, 0
    for d in rows[start:]:
        m = d.get("message") or {}
        u = m.get("usage")
        if d.get("type") != "assistant" or not u or m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        new += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
        cached += u.get("cache_read_input_tokens", 0)
        out += u.get("output_tokens", 0)

    local = 0
    try:
        for line in LEDGER.read_text().splitlines():
            r = json.loads(line)
            if r.get("ts", 0) >= turn_start:
                local += r.get("in", 0) + r.get("out", 0)
    except (OSError, ValueError):
        pass

    total = new + cached + out
    msg = (f"🔴 Claude: {total:,} tokens this turn ({new + out:,} new · {cached:,} re-read from cache)\n"
           f"🟢 Local models: {local:,} tokens handled on this machine, not billed to Claude")
    print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    main()
