#!/usr/bin/env python3
"""
local_first_hook.py - Claude Code hooks that push work onto the local models (Ollama) before Claude writes it.

  UserPromptSubmit  adds a one-line "local models first" reminder to every prompt you send.
  PreToolUse:Write  blocks creating a NEW file of more than MIN_LINES lines unless a local-evolve tool
                    (local_draft / local_evolve / local_result) was called since your last message.
                    Edits and overwrites of existing files are never blocked, and nothing is blocked
                    while Ollama is offline.

Registered in ~/.claude/settings.json. Standard library only; any internal error lets the action through.
Set LOCAL_FIRST_OFF=1 in the environment to disable both without editing settings.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from token_footer import is_prompt  # noqa: E402  (same "message you typed" test the footer uses)

MIN_LINES = 50
# Both registrations count: "local-evolve" (desktop app, chat preset) and "local-evolve-code" (Claude Code).
LOCAL_TOOLS = tuple(f"mcp__{server}__{tool}" for server in ("local-evolve", "local-evolve-code")
                    for tool in ("local_draft", "local_evolve", "local_result"))
REMINDER = ("Local models first: draft any new file over ~50 lines with local_draft/local_evolve before writing it, "
            "check local_models if unsure Ollama is up, and say which parts you did without them and why.")


def local_tool_used_this_turn(transcript: str) -> bool:
    rows = []
    with open(transcript) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    start = max((i for i, d in enumerate(rows) if is_prompt(d)), default=0)
    for d in rows[start:]:
        content = (d.get("message") or {}).get("content")
        if isinstance(content, list) and any(b.get("type") == "tool_use" and b.get("name") in LOCAL_TOOLS
                                             for b in content if isinstance(b, dict)):
            return True
    return False


def ollama_up() -> bool:
    try:
        host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        urllib.request.urlopen(f"{host if host.startswith('http') else 'http://' + host}/api/tags", timeout=1.5)
        return True
    except OSError:
        return False


def main() -> None:
    if os.environ.get("LOCAL_FIRST_OFF"):
        return
    try:
        hook = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    event = hook.get("hook_event_name")

    if event == "UserPromptSubmit":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": REMINDER}}))
        return

    if event == "PreToolUse" and hook.get("tool_name") == "Write":
        inp = hook.get("tool_input") or {}
        path, content = inp.get("file_path", ""), inp.get("content", "")
        if not path or Path(path).exists() or content.count("\n") + 1 <= MIN_LINES:
            return
        try:
            if local_tool_used_this_turn(hook["transcript_path"]):
                return
        except (KeyError, OSError):
            return
        if not ollama_up():
            print(json.dumps({"systemMessage": "local_first_hook: Ollama is offline, so this write was allowed. "
                                               "Run `python3 start_ollama.py` to use the local models."}))
            return
        reason = (f"Blocked by local_first_hook: {Path(path).name} is a new {content.count(chr(10)) + 1}-line file and no "
                  "local model was used this turn. Draft it with mcp__local-evolve__local_draft (or local_evolve) first, "
                  "then review and write it.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never break Claude Code over a reminder
