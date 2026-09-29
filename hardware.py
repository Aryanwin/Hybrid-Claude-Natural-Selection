#!/usr/bin/env python3
"""
hardware.py - detect this computer's memory / GPU and pick settings the local models will fit in.

Every other script reads its defaults from load_config(), so the same repo runs well on an 8 GB laptop
and on a 64 GB workstation. Precedence (highest first):

    command-line flags  >  EVOLVE_* env vars  >  evolve.config.json  >  auto-detected profile

    python3 hardware.py                   show what was detected and the settings that will be used
    python3 hardware.py --profile small   preview another profile
    python3 hardware.py --write           save the choice to evolve.config.json (add --profile to pin one)
    python3 hardware.py --env             shell exports for the Ollama server (used by start_ollama)
    python3 hardware.py --models          the model names, one per line (used by install.py)
    python3 hardware.py --json            everything as JSON

Standard library only. Detection never raises: anything it can't read falls back to conservative values.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "evolve.config.json"

# budget_gb = memory the models may use. Each profile fits its largest model (Q4) plus the KV cache for
# `parallel` slots of `ctx` tokens (q8 cache) inside that budget, one model loaded at a time unless noted.
PROFILES = {
    "tiny": {"min_budget_gb": 0, "models": ["qwen2.5-coder:3b", "qwen2.5-coder:1.5b"],
             "parallel": 1, "ctx": 8192, "max_loaded": 1, "threads": 2,
             "description": "under ~7 GB for models: 8 GB laptops, CPU-only machines"},
    "small": {"min_budget_gb": 7, "models": ["qwen2.5-coder:7b", "qwen2.5-coder:3b"],
              "parallel": 2, "ctx": 8192, "max_loaded": 1, "threads": 3,
              "description": "~7-12 GB: 16 GB Macs, 8-12 GB GPUs"},
    "medium": {"min_budget_gb": 12, "models": ["qwen2.5-coder:14b", "deepseek-coder-v2:16b", "qwen2.5-coder:7b"],
               "parallel": 3, "ctx": 16384, "max_loaded": 1, "threads": 4,
               "description": "~12-20 GB: 18-24 GB Macs, 16 GB GPUs"},
    "large": {"min_budget_gb": 20, "models": ["qwen2.5-coder:14b", "deepseek-coder-v2:16b", "qwen2.5-coder:7b"],
              "parallel": 4, "ctx": 24576, "max_loaded": 1, "threads": 5,
              "description": "~20-28 GB: 32 GB Macs, 24 GB GPUs (same models, more slots and context)"},
    "xl": {"min_budget_gb": 28, "models": ["qwen3-coder:30b", "qwen2.5-coder:14b", "deepseek-coder-v2:16b"],
           "parallel": 4, "ctx": 24576, "max_loaded": 1, "threads": 5,
           "description": "~28-48 GB: 36-64 GB Macs, 32-48 GB of GPU memory"},
    "xxl": {"min_budget_gb": 48, "models": ["qwen2.5-coder:32b", "qwen3-coder:30b", "deepseek-coder-v2:16b"],
            "parallel": 4, "ctx": 32768, "max_loaded": 2, "threads": 6,
            "description": "48 GB+: 64 GB+ Macs, multi-GPU workstations (two models stay loaded)"},
}
SETTINGS = ("models", "parallel", "ctx", "max_loaded", "threads")
_cache: dict | None = None


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _ram_gb() -> float:
    try:
        if sys.platform == "darwin":
            return int(_run(["sysctl", "-n", "hw.memsize"])) / 1024 ** 3
        if sys.platform.startswith("linux"):
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024 ** 2
        if sys.platform == "win32":
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return stat.ullTotalPhys / 1024 ** 3
    except (OSError, ValueError, AttributeError):
        pass
    return 8.0  # unknown: assume a small machine


def _nvidia_gb() -> float:
    out = _run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"])
    try:
        return sum(int(x) for x in out.split()) / 1024
    except ValueError:
        return 0.0


def detect() -> dict:
    osname = {"darwin": "macos", "win32": "windows"}.get(sys.platform, "linux")
    arch = platform.machine().lower()
    ram = _ram_gb()
    chip = (_run(["sysctl", "-n", "machdep.cpu.brand_string"]) if osname == "macos" else "") \
        or platform.processor() or arch
    if osname == "macos" and arch == "arm64":
        # Unified memory. macOS lets the GPU wire ~2/3 of RAM (<=36 GB) or ~3/4 (larger) by default.
        gpu, vram, budget = "apple", ram, ram * (0.66 if ram <= 36 else 0.75)
    elif (vram := _nvidia_gb()) > 0:
        gpu, budget = "nvidia", vram * 0.9
    else:
        gpu, vram, budget = "none", 0.0, ram * 0.5  # CPU inference: leave half the RAM for everything else
    return {"os": osname, "arch": arch, "chip": chip, "ram_gb": round(ram, 1), "gpu": gpu,
            "vram_gb": round(vram, 1), "budget_gb": round(budget, 1)}


def pick_profile(hw: dict) -> str:
    fits = [n for n, p in PROFILES.items() if p["min_budget_gb"] <= hw["budget_gb"]]
    if hw["gpu"] == "none":
        fits = [n for n in fits if n in ("tiny", "small")]  # CPU is too slow for 14B+ in a loop
    return max(fits, key=lambda n: PROFILES[n]["min_budget_gb"]) if fits else "tiny"


def _profile(name: str) -> dict:
    if name not in PROFILES:
        sys.exit(f"unknown profile {name!r}; choose from: {', '.join(PROFILES)}")
    return {"profile": name, **{k: PROFILES[name][k] for k in SETTINGS}}


def load_config(profile: str | None = None) -> dict:
    """Merged settings: auto profile < evolve.config.json < EVOLVE_* env vars (< `profile` argument)."""
    global _cache
    if _cache is not None and profile is None:
        return _cache
    hw = detect()
    saved = {}
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text())
        except (OSError, json.JSONDecodeError) as e:
            print(f"warning: ignoring unreadable {CONFIG_PATH.name}: {e}", file=sys.stderr)
    name = profile or os.environ.get("EVOLVE_PROFILE") or saved.get("profile") or pick_profile(hw)
    cfg = _profile(name)
    cfg.update({k: v for k, v in saved.items() if k in SETTINGS})
    env = os.environ
    if env.get("EVOLVE_MODELS"):
        cfg["models"] = [m.strip() for m in env["EVOLVE_MODELS"].split(",") if m.strip()]
    for key, var in (("ctx", "EVOLVE_CTX"), ("parallel", "EVOLVE_PARALLEL"),
                     ("max_loaded", "EVOLVE_MAX_LOADED"), ("threads", "EVOLVE_THREADS")):
        if env.get(var, "").isdigit():
            cfg[key] = int(env[var])
    cfg["auto_profile"] = pick_profile(hw)
    cfg["hardware"] = hw
    if profile is None:
        _cache = cfg
    return cfg


def report(cfg: dict) -> str:
    hw = cfg["hardware"]
    gpu = {"apple": f"Apple unified memory ({hw['vram_gb']} GB shared)",
           "nvidia": f"NVIDIA, {hw['vram_gb']} GB VRAM", "none": "none found (CPU inference)"}[hw["gpu"]]
    why = "auto-detected" if cfg["profile"] == cfg["auto_profile"] else f"overridden (auto pick: {cfg['auto_profile']})"
    return "\n".join([
        f"Machine:   {hw['chip']} · {hw['os']}/{hw['arch']} · {hw['ram_gb']} GB RAM",
        f"GPU:       {gpu}",
        f"Budget:    ~{hw['budget_gb']} GB for models + context",
        f"Profile:   {cfg['profile']} ({why}): {PROFILES[cfg['profile']]['description']}",
        f"Models:    {', '.join(cfg['models'])}",
        f"Ollama:    {cfg['parallel']} parallel slots x {cfg['ctx']} tokens, {cfg['max_loaded']} model(s) loaded",
        f"evolve.py: {cfg['threads']} threads per round",
        f"Config:    {CONFIG_PATH if CONFIG_PATH.exists() else '(no evolve.config.json; using the auto profile)'}",
    ])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=list(PROFILES), help="use this profile instead of the auto pick")
    ap.add_argument("--write", action="store_true", help=f"save the profile to {CONFIG_PATH.name}")
    ap.add_argument("--env", action="store_true", help="print shell exports for `ollama serve`")
    ap.add_argument("--models", action="store_true", help="print model names, one per line")
    ap.add_argument("--json", action="store_true", help="print everything as JSON")
    args = ap.parse_args()
    cfg = load_config(args.profile)

    if args.write:
        saved = {"profile": cfg["profile"]}
        if CONFIG_PATH.exists():  # keep hand-edited overrides (models, ctx, ...) unless the profile changed
            old = json.loads(CONFIG_PATH.read_text())
            if old.get("profile") == cfg["profile"]:
                saved.update({k: v for k, v in old.items() if k in SETTINGS})
        CONFIG_PATH.write_text(json.dumps(saved, indent=2) + "\n")
        print(f"wrote {CONFIG_PATH}: {json.dumps(saved)}")
    elif args.env:
        print(f"export OLLAMA_NUM_PARALLEL={cfg['parallel']}")
        print(f"export OLLAMA_CONTEXT_LENGTH={cfg['ctx']}")
        print(f"export OLLAMA_MAX_LOADED_MODELS={cfg['max_loaded']}")
    elif args.models:
        print("\n".join(cfg["models"]))
    elif args.json:
        print(json.dumps(cfg, indent=2))
    else:
        print(report(cfg))


if __name__ == "__main__":
    main()
