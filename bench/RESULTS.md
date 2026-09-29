# Benchmark results

14 tasks, each solved three ways and scored by hidden grader tests (`bench/graders/`, verified against `bench/reference/`). Claude tokens are exact (`claude -p --output-format json`); local tokens are Ollama's own counts. "Claude tokens" = new input + cache writes + output + cache reads; cache reads cost ~10% of new input.

## Summary

| | Claude Code (agentic) | Claude one-shot | Hybrid (this repo) |
|---|---|---|---|
| Tasks fully correct | 14/14 | 14/14 | 13/14 |
| Grader tests passed | 98/98 | 98/98 | 91/98 |
| Claude tokens (total) | 1,425.9K | 32.6K | 193.1K |
| …of which new (not cache reads) | 191.4K | 32.6K | 193.1K |
| …of which Claude wrote (output) | 29.7K | 11.7K | 67.1K |
| Claude cost at API prices | $1.19 | $0.20 | $1.17 |
| Local tokens (free) | 0 | 0 | 391.0K |
| Wall time (sum) | 4 min | 2 min | 63 min |

**Hybrid vs. the others** (Claude cost at API prices, which weights output and cache reads correctly):

- vs Claude Code (agentic): saves 1% ($1.17 vs $1.19); Claude tokens 193.1K vs 1,425.9K
- vs Claude one-shot: costs 486% ($1.17 vs $0.20); Claude tokens 193.1K vs 32.6K

## Per task

Graders passed · Claude tokens (total / new) · cost · local tokens

| Task | Kind | Claude Code (agentic) | Claude one-shot | Hybrid (this repo) |
|---|---|---|---|---|
| `lru` | algorithm | ✅ 8/8 · 95.8K / 12.4K · $0.076 | ✅ 8/8 · 1.8K / 1.8K · $0.009 | ✅ 8/8 · 9.8K / 9.8K · $0.065 · 8.7K local |
| `dijkstra` | algorithm | ✅ 8/8 · 98.0K / 13.8K · $0.085 | ✅ 8/8 · 2.5K / 2.5K · $0.015 | ✅ 8/8 · 28.8K / 28.8K · $0.154 · 73.4K local |
| `roman` | parsing | ✅ 5/5 · 130.1K / 14.1K · $0.092 | ✅ 5/5 · 2.6K / 2.6K · $0.017 | ✅ 5/5 · 20.1K / 20.1K · $0.113 · 33.8K local |
| `intervals` | algorithm | ✅ 8/8 · 129.4K / 13.8K · $0.091 | ✅ 8/8 · 1.9K / 1.9K · $0.011 | ✅ 8/8 · 5.1K / 5.1K · $0.039 · 6.3K local |
| `toposort` | algorithm | ✅ 8/8 · 96.1K / 12.6K · $0.077 | ✅ 8/8 · 1.9K / 1.9K · $0.011 | ✅ 8/8 · 5.7K / 5.7K · $0.045 · 6.4K local |
| `levenshtein` | algorithm | ✅ 7/7 · 95.5K / 12.2K · $0.074 | ✅ 7/7 · 2.0K / 2.0K · $0.011 | ✅ 7/7 · 11.0K / 11.0K · $0.073 · 7.4K local |
| `calc` | parsing | ✅ 7/7 · 97.2K / 14.9K · $0.092 | ✅ 7/7 · 3.1K / 3.1K · $0.022 | ❌ 0/7 · 37.0K / 37.0K · $0.184 · 136.2K local |
| `knapsack` | algorithm | ✅ 7/7 · 97.6K / 13.6K · $0.084 | ✅ 7/7 · 2.3K / 2.3K · $0.014 | ✅ 7/7 · 10.6K / 10.6K · $0.070 · 27.1K local |
| `autocomplete` | data structure | ✅ 6/6 · 127.6K / 13.2K · $0.087 | ✅ 6/6 · 1.9K / 1.9K · $0.010 | ✅ 6/6 · 9.9K / 9.9K · $0.065 · 7.8K local |
| `duration` | parsing | ✅ 7/7 · 97.7K / 13.5K · $0.083 | ✅ 7/7 · 2.6K / 2.6K · $0.016 | ✅ 7/7 · 11.1K / 11.1K · $0.071 · 9.0K local |
| `justify` | text | ✅ 7/7 · 131.8K / 15.4K · $0.100 | ✅ 7/7 · 2.3K / 2.3K · $0.014 | ✅ 7/7 · 10.3K / 10.3K · $0.067 · 6.5K local |
| `rle` | text | ✅ 6/6 · 97.9K / 13.8K · $0.086 | ✅ 6/6 · 2.7K / 2.7K · $0.018 | ✅ 6/6 · 19.6K / 19.6K · $0.114 · 31.9K local |
| `matrix` | algorithm | ✅ 7/7 · 64.6K / 13.0K · $0.074 | ✅ 7/7 · 2.1K / 2.1K · $0.013 | ✅ 7/7 · 6.6K / 6.6K · $0.054 · 8.5K local |
| `sudoku` | algorithm | ✅ 7/7 · 66.7K / 15.2K · $0.089 | ✅ 7/7 · 2.8K / 2.8K · $0.019 | ✅ 7/7 · 7.5K / 7.5K · $0.063 · 28.0K local |
