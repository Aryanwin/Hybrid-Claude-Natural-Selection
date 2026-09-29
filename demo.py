#!/usr/bin/env python3
"""
demo.py - try evolve.py on a throwaway copy of examples/demo (a slugify task); your projects are untouched.

    python3 demo.py            local models only, bundled tests: zero Claude usage
    python3 demo.py --claude   Claude writes spec + hidden tests, reviews threads, judges

Extra flags go to evolve.py, e.g.  python3 demo.py --threads 2 --models qwen2.5-coder:7b
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO = Path.home() / ".cache" / "evolve" / "demo-repo"
TASK = ("Add slugify(title, max_len=60) to mypkg/text.py: lowercase, accents folded to ASCII, other non-ASCII "
        "dropped, words of letters/digits joined by '-', apostrophes removed without splitting words, at most "
        "max_len chars cut on a word boundary (hard-cut a single over-long word), raise TypeError for non-strings.")


def git(*a: str) -> None:
    subprocess.run(["git", "-c", "user.name=evolve", "-c", "user.email=evolve@localhost", *a], cwd=DEMO, check=True,
                   capture_output=True)


extra = sys.argv[1:]
use_claude = "--claude" in extra
if use_claude:
    extra.remove("--claude")
shutil.rmtree(DEMO, ignore_errors=True)
shutil.copytree(HERE / "examples" / "demo", DEMO)
git("init", "-q")
git("add", "-A")
git("commit", "-qm", "demo start")
print(f"Demo repo: {DEMO}", flush=True)

cmd = [sys.executable, str(HERE / "evolve.py"), TASK, "--files", "mypkg/text.py"]
if use_claude:
    git("rm", "-q", "tests/test_slugify.py")
    git("commit", "-qm", "let Claude write the tests")
else:
    cmd += ["--tests", "tests/test_slugify.py", "--no-claude"]
code = subprocess.run(cmd + extra, cwd=DEMO).returncode
print(f"\nResult in {DEMO}:")
subprocess.run(["git", "--no-pager", "diff", "--stat"], cwd=DEMO)
sys.exit(code)
