#!/usr/bin/env python3
"""
chart.py - compare benchmark runs across Claude models: cost, tasks solved, Claude tokens.

    python3 bench/chart.py haiku=bench/results/results-haiku.json \
        sonnet=bench/results/results-sonnet.json opus=bench/results/results-opus.json --out bench/chart

Writes <out>-light.svg / <out>-dark.svg (+ .png). Three small multiples instead of one chart with two scales;
colors are the dataviz reference palette's first three slots, validated for color-vision deficiency in both
themes. Every bar carries its value, since one light-mode slot sits just under 3:1 contrast.
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ALL_MODES = [("agentic", "Claude Code\n(agentic)"), ("oneshot", "Claude\none-shot"), ("hybrid", "Hybrid\n(v1)"),
             ("hybrid2", "Hybrid v2\n(+ near-miss,\ndisputes)"), ("hybrid3", "Hybrid v3\n(+ cost cuts)"),
             ("auto", "Auto\n(one-shot first)")]
MODES = ALL_MODES[:3]
THEMES = {
    "light": {"surface": "#fcfcfb", "text": "#0b0b0b", "muted": "#52514e", "grid": "#e4e3df",
              "series": ["#2a78d6", "#eb6834", "#1baf7a"]},
    "dark": {"surface": "#1a1a19", "text": "#ffffff", "muted": "#c3c2b7", "grid": "#3a3936",
             "series": ["#3987e5", "#d95926", "#199e70"]},
}


def load_rows(spec: str) -> list[dict]:
    """FILE or FILE+V2FILE: rows of FILE, plus the hybrid rows of V2FILE relabelled as mode "hybrid2"."""
    first, *rest = spec.split("+")
    rows = json.loads(Path(first).read_text())
    for i, extra in enumerate(rest, 2):
        for r in json.loads(Path(extra).read_text()):
            if r["mode"] == "hybrid":
                rows.append({**r, "mode": f"hybrid{i}"})
            elif r["mode"] == "auto":
                rows.append(r)
    return rows


def short(n: float) -> str:
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.0f}K" if n >= 1e3 else f"{n:.0f}"


def aggregate(rows: list[dict]) -> dict:
    out = {}
    for mode, _ in MODES:
        rs = [r for r in rows if r["mode"] == mode]
        out[mode] = {"cost": sum(r["cost_usd"] for r in rs), "n": len(rs),
                     "solved": sum(1 for r in rs if r["passed"] == r["total"] > 0),
                     "tokens": sum(r["claude_new"] + r["claude_cached"] for r in rs)}
    return out


def draw(data: dict[str, dict], theme: dict, path: Path) -> None:
    labels = list(data)
    n_tasks = max(v["n"] for d in data.values() for v in d.values())
    panels = [("cost", "Claude cost at API prices", lambda v: f"${v:.2f}"),
              ("solved", f"Tasks fully correct (of {n_tasks})", lambda v: f"{v:.0f}"),
              ("tokens", "Claude tokens used", short)]
    width = 0.8 / len(labels)
    # Four groups of three bars don't leave room for value labels side by side: stack the panels instead.
    stacked = len(MODES) > 3
    fig, axes = plt.subplots(3, 1, figsize=(12, 11)) if stacked else plt.subplots(1, 3, figsize=(13, 4.4))
    fig.set_facecolor(theme["surface"])
    for ax, (key, title, fmt) in zip(axes, panels):
        ax.set_facecolor(theme["surface"])
        top = max(d[m][key] for d in data.values() for m, _ in MODES)
        for j, label in enumerate(labels):
            xs = [i + (j - (len(labels) - 1) / 2) * width for i in range(len(MODES))]
            vals = [data[label][m][key] for m, _ in MODES]
            ax.bar(xs, vals, width, color=theme["series"][j], edgecolor=theme["surface"], linewidth=2, zorder=3,
                   label=label.capitalize())
            for x, v in zip(xs, vals):
                ax.text(x, v + top * 0.015, fmt(v), ha="center", va="bottom", fontsize=7.5, color=theme["muted"])
        ax.set_ylim(0, (n_tasks + 1.5) if key == "solved" else top * 1.15)
        names = [name.replace("\n", " ").replace("( ", "(") for _, name in MODES] if stacked else [n for _, n in MODES]
        ax.set_xticks(range(len(MODES)), names, fontsize=9, color=theme["text"])
        ax.tick_params(axis="y", labelsize=8, colors=theme["muted"], length=0)
        ax.tick_params(axis="x", length=0)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _, f=fmt: f(v)))
        ax.grid(axis="y", color=theme["grid"], linewidth=0.8, zorder=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(theme["grid"])
        ax.set_title(title, loc="left", fontsize=11, color=theme["text"], pad=10)
    fig.suptitle(f"Same {n_tasks} tasks, {len(labels)} Claude models", x=0.012, ha="left", fontsize=13,
                 color=theme["text"], fontweight="bold")
    handles, names = axes[0].get_legend_handles_labels()
    leg = fig.legend(handles, names, loc="upper right", ncol=len(labels), frameon=False, fontsize=9,
                     bbox_to_anchor=(0.995, 1.0))
    for t in leg.get_texts():
        t.set_color(theme["text"])
    fig.tight_layout(rect=(0, 0, 1, 0.965 if stacked else 0.94), h_pad=2.5)
    for ext in ("svg", "png"):
        fig.savefig(path.with_name(f"{path.name}.{ext}"), dpi=200, facecolor=theme["surface"])
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", metavar="LABEL=FILE[+V2FILE]")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "chart"))
    args = ap.parse_args()
    global MODES
    data, seen = {}, set()
    for item in args.runs:
        label, file = item.split("=", 1)
        rows = load_rows(file)
        seen |= {r["mode"] for r in rows}
        data[label] = rows
    MODES = [m for m in ALL_MODES if m[0] in seen]
    data = {label: aggregate(rows) for label, rows in data.items()}
    for name, theme in THEMES.items():
        draw(data, theme, Path(f"{args.out}-{name}"))
        print(f"wrote {args.out}-{name}.svg / .png")


if __name__ == "__main__":
    main()
