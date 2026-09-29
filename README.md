# claude-local-evolve

Free local LLMs (via [Ollama](https://ollama.com)) do the bulk writing in a Darwinian evolution loop: several
models write competing attempts in parallel "threads", tests score them, weak threads get pruned, strong ones
mutate and crossbreed. Claude (via [Claude Code](https://claude.com/claude-code)) only plans, reviews the threads
(kill / keep / refine / fork) and judges the winner, so a typical task costs 1–5 short Claude calls.

It adapts to the computer it runs on: `hardware.py` detects memory and GPU and picks models, parallelism and
context sizes that fit, from an 8 GB laptop to a 64 GB+ workstation.

```
task ─► Claude: spec + visible tests + hidden tests                               (1 call)
     ─► N threads, each owned by a local model from this machine's profile
     ─► every round, all local and free:
          mutate   each thread's fittest attempt, with its own test failures fed back
          cross    two threads passing DIFFERENT tests → one child merges them
          score    pytest, each candidate in its own git worktree
          select   thread keeps its fittest · identical threads dropped ·
                   no progress for 2 rounds → pruned, a fresh thread takes its place
     ─► every 2 rounds Claude reads a compact digest of all threads          (1 call each)
          keep · kill (dead end) · refine (pointed hint) · fork (clone onto another model)
     ─► visible-test passers must also pass hidden tests (catches test-gaming)
     ─► 2+ finalists? Claude picks one from the diffs                         (1 call)
     ─► winner + tests written into your working tree; you review with git diff
```

## What's inside

| File | What it does |
|---|---|
| `evolve.py` | The coding loop above. Fitness = pytest. |
| `evolve_chat.py` | The same tournament for non-code work (drafts, summaries, brainstorming): local models write, a local judge runs pairwise duels, survivors are revised from critiques. |
| `mcp_server.py` | Exposes `local_evolve`, `local_draft`, `local_result`, `local_models` to the Claude desktop app and Claude Code. |
| `hardware.py` | Detects RAM / GPU and picks a profile (models, parallel slots, context, threads). Everything else reads it. |
| `install.py` | One-time setup: profile, Ollama, the profile's models, pytest, Claude Code CLI check. |
| `start_ollama.py` | Runs `ollama serve` with the profile's settings. Leave it running. |
| `demo.py` | Runs `evolve.py` on a throwaway copy of `examples/demo`. |
| `install_hooks.py` | 🔴/🟢 token footer after every Claude Code reply; optional "local-first" hooks. |
| `register_mcp.py` | Adds the MCP server to the Claude desktop app (macOS, Windows, Linux). |
| `bench/` | 14-task benchmark: agentic Claude Code vs one-shot Claude vs the hybrid, graded by hidden tests. |
| `healthcheck/checkers.py` | A local model plays checkers against a minimax bot. Checks every model and both token trackers, then opens a visual replay. |

Standard library only; no `pip install` beyond `pytest`.

## Requirements

- Python 3.9+ and git
- macOS (Apple Silicon recommended), Linux, or Windows
- 5–60 GB free disk, depending on the profile
- [Ollama](https://ollama.com/download) (`install.py` installs it with Homebrew on macOS, and tells you how elsewhere)
- Optional: [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) with a Claude account, for planning,
  reviews and judging. Without it, use `evolve.py --tests your_tests.py --no-claude`.

## Quick start

```bash
git clone https://github.com/Aryanwin/claude-local-evolve.git
cd claude-local-evolve
python3 install.py
```

Then, in its own terminal (leave it running):

```bash
python3 start_ollama.py
```

Try it:

```bash
python3 demo.py                                        # local models only, zero Claude usage
python3 demo.py --claude                               # the full hybrid
python3 healthcheck/checkers.py --model all --quiet    # check every local model + the trackers
```

On Windows use `py` instead of `python3`.

## Hardware profiles

| Profile | Model budget | Typical machine | Models | Parallel × context |
|---|---|---|---|---|
| `tiny` | < 7 GB | 8 GB laptops, CPU-only | qwen2.5-coder 3b, 1.5b | 1 × 8K |
| `small` | 7–12 GB | 16 GB Macs, 8–12 GB GPUs | qwen2.5-coder 7b, 3b | 2 × 8K |
| `medium` | 12–20 GB | 18–24 GB Macs, 16 GB GPUs | qwen2.5-coder 14b, deepseek-coder-v2 16b, qwen2.5-coder 7b | 3 × 16K |
| `large` | 20–28 GB | 32 GB Macs, 24 GB GPUs | same as medium | 4 × 24K |
| `xl` | 28–48 GB | 36–64 GB Macs, 32–48 GB of GPU memory | qwen3-coder 30b, qwen2.5-coder 14b, deepseek-coder-v2 16b | 4 × 24K |
| `xxl` | 48 GB+ | 64 GB+ Macs, multi-GPU workstations | qwen2.5-coder 32b, qwen3-coder 30b, deepseek-coder-v2 16b | 4 × 32K, 2 models loaded |

**Model budget** is the memory the models may use: about 2/3 of RAM on Apple Silicon (3/4 above 36 GB, matching
macOS's default GPU limit), 90% of VRAM on NVIDIA, and half of RAM on CPU-only machines (capped at `small`,
because CPU inference is too slow for bigger models in a loop).

```bash
python3 hardware.py                          # what was detected, and the settings that will be used
python3 hardware.py --profile small          # preview another profile
python3 hardware.py --profile small --write  # pin it (saved to evolve.config.json)
```

Settings are resolved in this order, highest first:

1. command-line flags (`evolve.py --models ... --ctx ...`)
2. environment variables: `EVOLVE_PROFILE`, `EVOLVE_MODELS` (comma list), `EVOLVE_CTX`, `EVOLVE_PARALLEL`,
   `EVOLVE_MAX_LOADED`, `EVOLVE_THREADS`
3. `evolve.config.json` (written by `install.py` / `hardware.py --write`; you can hand-edit `models`, `ctx`, ...)
4. the auto-detected profile

**Why profiles avoid swap:** a model is read in full for every token it generates. Once any part of it spills to
disk, speed drops from ~15–25 tokens/s to under 1. Each profile keeps the largest model plus the context for
every parallel slot inside the budget, and loads one model at a time (evolve runs all of one model's jobs, then
switches).

## Using it on your code

Run from inside your project's git repo, with your work committed:

```bash
python3 /path/to/claude-local-evolve/evolve.py \
    "Add slugify(title) to text.py: lowercase, ASCII only, words joined by '-', max 60 chars" \
    --files mypkg/text.py --context mypkg/models.py
```

Claude is called through `claude -p` with no tools, a two-line system prompt and `--strict-mcp-config`, so each
call carries ~1.3K tokens of fixed overhead instead of Claude Code's usual ~28K (plus ~70K more if you have
MCP connectors such as Gmail or Drive connected; they're loaded into every call otherwise). Usage is read from
`--output-format json`, so the numbers the script prints are exact.

The winning change and its tests land in your working tree; review with `git diff`. The script prints the undo
command and a per-model scoreboard. Logs and patches are kept in `~/.cache/evolve/<repo>/<timestamp>/`.

| Flag | Default | What it does |
|---|---|---|
| `--files` | – | Files the local models may edit (1–3, ideally under ~300 lines) |
| `--context` | – | Read-only files they should see |
| `--models a,b,c` | profile | Local model roster, assigned to threads round-robin |
| `--threads` | profile | Live threads per round |
| `--rounds` | 8 | Maximum rounds |
| `--review-every` | 2 | Claude reviews the threads every N rounds (0 = never) |
| `--claude-budget` | 6 | Hard cap on Claude calls per run (one is kept for the judge) |
| `--claude-model sonnet` | your default | Cheaper Claude model for planning, reviews and judging |
| `--tests f.py --no-claude` | – | Your own tests, no Claude at all |
| `--full-suite` | off | Finalists must also pass your whole existing test suite |

## Claude desktop app and Claude Code (MCP)

The MCP server lets Claude hand bulky writing to the local tournament and read back only the finalists.

```bash
python3 register_mcp.py                                   # Claude desktop app (Chat / Cowork)
claude mcp add local-evolve -- python3 "$PWD/mcp_server.py"   # Claude Code
```

Quit the desktop app completely before running `register_mcp.py`: a running app can rewrite its config from
memory and drop the change. Reopen it afterwards.

| Tool | What it does |
|---|---|
| `local_evolve` | Tournament: drafts across the roster, pairwise duels judged locally, revisions, top finalists back to Claude. 1–8 min, so it returns a `job_id` after ~40 s. |
| `local_draft` | n plain drafts, no judging |
| `local_result` | Keep waiting on a `job_id` |
| `local_models` | Is Ollama up, which models write and judge |

## Token footer

```bash
python3 install_hooks.py
```

After every Claude Code reply:

```
🔴 Claude: 184,203 tokens this turn (3,412 new · 180,791 re-read from cache)
🟢 Local models: 12,880 tokens handled on this machine, not billed to Claude
```

Both numbers are exact: Claude's from the session transcript's usage records, the local count from Ollama's own
token counts (logged to `~/.cache/evolve/ledger.jsonl` by every local call). "Re-read from cache" is the
conversation Claude re-reads on each step, which costs a fraction of new tokens.

`python3 install_hooks.py --local-first` also adds hooks and a `~/.claude/CLAUDE.md` rule that make Claude Code
draft big new files with the local models first. `--remove` undoes everything; a backup of your settings is made
on every run.

## Benchmark: is it actually cheaper?

14 single-file tasks (LRU cache, Dijkstra, sudoku, an expression parser, knapsack, text justification, ...), each
solved three ways with each of three Claude models, and scored by hidden grader tests that no approach sees.
Claude usage is exact, from `claude -p --output-format json`; local models ran on the `medium` profile
(24 GB M5 Pro). Full per-task tables: [bench/RESULTS.md](bench/RESULTS.md).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="bench/chart-dark.svg">
  <img alt="Claude cost, tasks solved and Claude tokens for Haiku 4.5, Sonnet 5.5 and Opus 5.5 across the three approaches" src="bench/chart-light.svg">
</picture>

| Approach | | Haiku 4.5 | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|---|
| **Claude Code (agentic)** | tasks correct | 14/14 | 14/14 | 14/14 |
| | Claude tokens | 9.20M | 1.43M | 2.20M |
| | cost at API prices | $2.38 | $1.19 | $2.66 |
| **Claude one-shot** | tasks correct | 12/14 | 14/14 | 14/14 |
| | Claude tokens | 124K | 33K | 35K |
| | cost at API prices | $0.56 | $0.20 | $0.45 |
| **Hybrid (this repo)** | tasks correct | 7/14 | 13/14 | 13/14 |
| | Claude tokens | 598K | 193K | 224K |
| | cost at API prices | $2.31 | $1.17 | $2.79 |
| | local tokens (free) | 973K | 391K | 429K |
| | wall time | 175 min | 63 min | 49 min |

*Agentic* is Claude Code working normally (tools on, writes and runs its own tests), measured without MCP
connectors; with connectors loaded it would cost ~70K more tokens per step. *One-shot* is a single minimal call
that just writes the module.

What this shows, honestly:

- **Against Claude Code working normally, the hybrid cuts Claude tokens by 86–90%** (Sonnet 1.43M → 193K,
  Opus 2.20M → 224K), **but not cost**: most agentic tokens are cheap cache reads, while every hybrid token is
  new and its planning step (spec + visible + hidden tests) writes a lot of output. Sonnet: $1.17 vs $1.19;
  Opus: $2.79 vs $2.66.
- **For small, precisely specified tasks, one Claude call is best** with Sonnet or Opus: 14/14, 6x cheaper than
  the hybrid, and done in minutes. The local models only write ~50–150 lines here, so there's little to offload.
- **Sonnet is the sweet spot** for every approach here. Opus solved the same tasks for 2.2–2.4x the price.
  Haiku is cheaper per token but not per task: it took 6.5x Sonnet's tokens as an agent, wrote 9x more output
  one-shot, and cost more than Sonnet in all three approaches.
- **The planner must be a strong model.** Haiku's hybrid "failed" 7 tasks, but in 5 of them the local models'
  code passes every benchmark grader: Haiku's own hidden tests had wrong expected values (e.g. "wednesday" →
  "saturday" is 6 edits, not 5), so correct code was rejected and the run kept evolving until it gave up.
  Opus's one hybrid failure (`levenshtein`) is the same thing: one wrong hidden test, correct code. Judged by the
  code itself, the local models solved 12/14 under Haiku and 14/14 under Opus.
- **The hybrid should pay off when the code is large relative to the spec**: Claude's cost is roughly fixed
  (plan, reviews, judge) while the local models do the writing. Passing your own tests (`--tests`) skips the
  planning call, the single largest cost.

Reproduce: `python3 bench/run_bench.py --check` (graders vs reference solutions), then
`python3 bench/run_bench.py --claude-model sonnet` (or `haiku` / `opus`), and
`python3 bench/chart.py haiku=... sonnet=... opus=...` for the chart.

## Good fits vs. bad fits

**Good fits:** a new function or class, a bug with a clear reproduction, parsing and validation, algorithms,
adding tests; long drafts, rewrites, summaries of long material, brainstorming many options.

**Bad fits:** vague goals ("make it cleaner"), UI work, changes spread across many files, anything tests can't
check, short factual questions (small models hallucinate), and debugging that needs running commands. Give
those to Claude directly.

## License

MIT, see [LICENSE](LICENSE).
