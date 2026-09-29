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
git clone https://github.com/USER/claude-local-evolve.git
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

## Good fits vs. bad fits

**Good fits:** a new function or class, a bug with a clear reproduction, parsing and validation, algorithms,
adding tests; long drafts, rewrites, summaries of long material, brainstorming many options.

**Bad fits:** vague goals ("make it cleaner"), UI work, changes spread across many files, anything tests can't
check, short factual questions (small models hallucinate), and debugging that needs running commands. Give
those to Claude directly.

## License

MIT, see [LICENSE](LICENSE).
