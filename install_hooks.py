#!/usr/bin/env python3
"""
install_hooks.py - add this repo's Claude Code hooks to ~/.claude/settings.json (merged, never replacing yours).

    python3 install_hooks.py                 🔴/🟢 token footer after every Claude Code reply (Stop hook)
    python3 install_hooks.py --local-first   also nudge Claude Code to draft new files with the local models:
                                             a reminder on every prompt, a block on writing big new files
                                             before a local tool was used, and a rule in ~/.claude/CLAUDE.md
    python3 install_hooks.py --remove        take all of them out again
    python3 install_hooks.py --dry-run       show the resulting settings without writing

Re-running is safe: old entries from this repo are replaced, not duplicated. A backup is written first.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLAUDE_DIR = Path.home() / ".claude"
SETTINGS = CLAUDE_DIR / "settings.json"
CLAUDE_MD = CLAUDE_DIR / "CLAUDE.md"
SCRIPTS = ("token_footer.py", "local_first_hook.py")


def cmd(script: str) -> str:
    # Absolute, quoted paths: Claude Code doesn't share your shell's PATH, and paths may contain spaces.
    return f'"{sys.executable}" "{HERE / script}"'


def entry(script: str, matcher: str | None = None) -> dict:
    e = {"hooks": [{"type": "command", "command": cmd(script), "timeout": 10}]}
    if matcher:
        e = {"matcher": matcher, **e}
    return e


def strip_ours(hooks: dict) -> int:
    """Remove every entry whose command runs one of this repo's scripts. Returns how many were removed."""
    removed = 0
    for event in list(hooks):
        keep = []
        for e in hooks[event]:
            cmds = " ".join(h.get("command", "") for h in e.get("hooks", []))
            if any(s in cmds for s in SCRIPTS):
                removed += 1
            else:
                keep.append(e)
        if keep:
            hooks[event] = keep
        else:
            del hooks[event]
    return removed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--local-first", action="store_true", help="also install the local-first hooks + CLAUDE.md rule")
    ap.add_argument("--remove", action="store_true", help="remove this repo's hooks")
    ap.add_argument("--dry-run", action="store_true", help="print the result, write nothing")
    args = ap.parse_args()

    try:
        settings = json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {}
    except json.JSONDecodeError as e:
        sys.exit(f"{SETTINGS} isn't valid JSON ({e}); fix it first. Nothing was changed.")
    hooks = settings.setdefault("hooks", {})
    removed = strip_ours(hooks)
    added = []
    if not args.remove:
        hooks.setdefault("Stop", []).append(entry("token_footer.py"))
        added.append("Stop: token footer")
        if args.local_first:
            hooks.setdefault("UserPromptSubmit", []).append(entry("local_first_hook.py"))
            hooks.setdefault("PreToolUse", []).append(entry("local_first_hook.py", "Write"))
            added += ["UserPromptSubmit: local-first reminder", "PreToolUse(Write): local-first guard"]
    if not hooks:
        del settings["hooks"]

    if args.dry_run:
        print(json.dumps(settings, indent=2))
        return
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS.exists():
        backup = SETTINGS.with_name(f"settings.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(SETTINGS, backup)
        print(f"backup: {backup}")
    SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")
    if removed:
        print(f"removed {removed} earlier hook entr{'y' if removed == 1 else 'ies'} from this repo")
    for a in added:
        print(f"added   {a}")

    if args.local_first:
        rule = (HERE / "templates" / "CLAUDE.md").read_text()
        existing = CLAUDE_MD.read_text() if CLAUDE_MD.exists() else ""
        if "local-evolve" in existing:
            print(f"kept    {CLAUDE_MD} (already mentions local-evolve)")
        else:
            CLAUDE_MD.write_text(existing + ("\n\n" if existing.strip() else "") + rule.replace("{REPO}", str(HERE)))
            print(f"added   local-models rule to {CLAUDE_MD}")
    print("Start a new Claude Code session to load the hooks.")


if __name__ == "__main__":
    main()
