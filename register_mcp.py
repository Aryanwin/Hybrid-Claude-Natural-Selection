#!/usr/bin/env python3
"""
register_mcp.py - add (or remove) the local-evolve MCP server in the Claude desktop app's config.

    python3 register_mcp.py            show the change, then apply it (a backup is written first)
    python3 register_mcp.py --dry-run  only show the change
    python3 register_mcp.py --remove   unregister

Quit the Claude desktop app completely BEFORE running this: a running app can rewrite its config from
memory and silently drop the change. Reopen it afterwards.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def config_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Claude" / "claude_desktop_config.json"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Claude" / "claude_desktop_config.json"


def app_running() -> bool:
    try:
        if sys.platform == "darwin":
            return subprocess.run(["pgrep", "-x", "Claude"], capture_output=True).returncode == 0
        if sys.platform == "win32":
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Claude.exe"], capture_output=True, text=True).stdout
            return "Claude.exe" in out
    except OSError:
        pass
    return False


CONFIG = config_path()
NAME = "local-evolve"
HERE = Path(__file__).resolve().parent


def main() -> None:
    if app_running() and "--dry-run" not in sys.argv and "--force" not in sys.argv:
        sys.exit("The Claude desktop app is running and may overwrite this change. Quit it completely "
                 "(Cmd+Q / File > Exit), then re-run. (--force to write anyway.)")
    cfg = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    servers = cfg.setdefault("mcpServers", {})
    if "--remove" in sys.argv:
        entry = servers.pop(NAME, None)
        print("not registered" if entry is None else f"removing {NAME}")
    else:
        # Absolute interpreter path: the desktop app doesn't see your shell's PATH (conda, pyenv, ...).
        entry = {"command": sys.executable, "args": [str(HERE / "mcp_server.py")]}
        print(f"{'updating' if NAME in servers else 'adding'} mcpServers.{NAME} in {CONFIG}:")
        print(json.dumps({NAME: entry}, indent=2))
        servers[NAME] = entry
    if "--dry-run" in sys.argv:
        print("(dry run: nothing written)")
        return
    if CONFIG.exists():
        backup = CONFIG.with_name(f"claude_desktop_config.backup-{time.strftime('%Y%m%d-%H%M%S')}.json")
        shutil.copy2(CONFIG, backup)
        print(f"backup: {backup}")
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    print("done. Open the Claude desktop app; local-evolve appears under Settings > Developer.")


if __name__ == "__main__":
    main()
