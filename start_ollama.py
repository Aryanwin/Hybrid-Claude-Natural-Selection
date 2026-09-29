#!/usr/bin/env python3
"""
start_ollama.py - run `ollama serve` tuned for this machine's profile (see hardware.py). Leave it running.

    python3 start_ollama.py
    python3 start_ollama.py --profile small     serve with another profile's settings

Env vars you set yourself (OLLAMA_NUM_PARALLEL, ...) win over the profile.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hardware  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--profile", choices=list(hardware.PROFILES))
cfg = hardware.load_config(ap.parse_args().profile)

if not shutil.which("ollama"):
    sys.exit("ollama isn't installed. Run: python3 install.py")
if sys.platform == "darwin" and subprocess.run(["pgrep", "-x", "Ollama"], capture_output=True).returncode == 0:
    sys.exit("The Ollama menu-bar app is running and ignores these settings. Quit it first (menu bar > Quit Ollama).")

env = dict(os.environ)
defaults = {
    "OLLAMA_NUM_PARALLEL": cfg["parallel"],       # evolve.py --parallel reads the same profile
    "OLLAMA_CONTEXT_LENGTH": cfg["ctx"],          # evolve.py --ctx reads the same profile
    "OLLAMA_MAX_LOADED_MODELS": cfg["max_loaded"],
    "OLLAMA_FLASH_ATTENTION": 1,                  # needed for the compressed KV cache below
    "OLLAMA_KV_CACHE_TYPE": "q8_0",               # halves context memory, negligible quality loss
    "OLLAMA_KEEP_ALIVE": "30m",                   # don't unload between rounds
}
for key, value in defaults.items():
    env.setdefault(key, str(value))

print(f"Profile {cfg['profile']}: {env['OLLAMA_NUM_PARALLEL']} parallel slots x {env['OLLAMA_CONTEXT_LENGTH']} tokens, "
      f"{env['OLLAMA_MAX_LOADED_MODELS']} model(s) loaded at once", flush=True)
try:
    sys.exit(subprocess.run(["ollama", "serve"], env=env).returncode)
except KeyboardInterrupt:
    pass
