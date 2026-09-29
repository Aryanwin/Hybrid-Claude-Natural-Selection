#!/usr/bin/env python3
"""
install.py - one-time setup on macOS, Linux or Windows. Safe to re-run: it skips whatever is already done.

    python3 install.py                  detect hardware, pick a profile, install Ollama + that profile's models
    python3 install.py --profile small  pin a different profile (see: python3 hardware.py)
    python3 install.py --skip-models    set up everything except the model downloads
"""
import argparse
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hardware  # noqa: E402

TAGS = "http://localhost:11434/api/tags"


def step(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)


def ollama_up() -> bool:
    try:
        urllib.request.urlopen(TAGS, timeout=3)
        return True
    except (urllib.error.URLError, OSError):
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=list(hardware.PROFILES), help="use this profile instead of the auto pick")
    ap.add_argument("--skip-models", action="store_true", help="don't download models")
    ap.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    args = ap.parse_args()

    step("Hardware")
    cfg = hardware.load_config(args.profile)
    print(hardware.report(cfg))
    if not args.yes and input("\nContinue with this profile? [Y/n] ").strip().lower() not in ("", "y", "yes"):
        print("Stopped. Preview others with `python3 hardware.py --profile NAME`.")
        sys.exit(0)
    cmd = [sys.executable, str(HERE / "hardware.py"), "--write"] + (["--profile", args.profile] if args.profile else [])
    subprocess.run(cmd, check=True)

    step("Ollama")
    if not shutil.which("ollama"):
        if sys.platform == "darwin" and shutil.which("brew"):
            subprocess.run(["brew", "install", "ollama"], check=True)
        elif sys.platform == "win32":
            sys.exit("Install Ollama from https://ollama.com/download (or: winget install Ollama.Ollama), then re-run.")
        elif sys.platform.startswith("linux"):
            sys.exit("Install Ollama with:  curl -fsSL https://ollama.com/install.sh | sh   then re-run.")
        else:
            sys.exit("Install Ollama from https://ollama.com/download, then re-run.")
    print(subprocess.run(["ollama", "--version"], capture_output=True, text=True).stdout.strip())

    failed = []
    if args.skip_models:
        step("Models: skipped (--skip-models)")
    else:
        step(f"Models for profile '{cfg['profile']}': {', '.join(cfg['models'])}")
        server = None
        if not ollama_up():
            print("(starting a temporary Ollama server for the downloads)")
            server = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(30):
                if ollama_up():
                    break
                time.sleep(0.5)
        try:
            for model in cfg["models"]:
                if subprocess.run(["ollama", "pull", model]).returncode != 0:
                    failed.append(model)
        finally:
            if server:
                server.terminate()
                server.wait()

    step("pytest")
    if subprocess.run([sys.executable, "-m", "pytest", "--version"]).returncode != 0:
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest"])

    step("Claude Code CLI")
    if shutil.which("claude"):
        print(subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip())
    else:
        print("`claude` isn't on your PATH (the desktop app doesn't add it). Install it with:")
        print("  irm https://claude.ai/install.ps1 | iex" if sys.platform == "win32"
              else "  curl -fsSL https://claude.ai/install.sh | bash")
        print("then run `claude` once to log in. Until then, use evolve.py with --tests and --no-claude.")

    step("Done" if not failed else "Done, with problems")
    if failed:
        print(f"These models failed to download: {', '.join(failed)}. Retry with `ollama pull <name>`.")
    print("Next:")
    print("  python3 start_ollama.py      # in its own terminal; leave it running")
    print("  python3 demo.py              # try evolve.py on a throwaway demo repo")
    print("  python3 healthcheck/checkers.py --model all --quiet   # check every local model")
    print("Optional:")
    print("  python3 install_hooks.py     # 🔴/🟢 token footer after every Claude Code reply")
    print("  python3 register_mcp.py      # local-evolve tools in the Claude desktop app")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
