# Benchmark results

14 single-file tasks, each solved three ways (Claude Code agentic, Claude one-shot, the hybrid) with each of three Claude models, and scored by hidden grader tests (`bench/graders/`, verified against `bench/reference/`). Claude usage is exact (`claude -p --output-format json`); local tokens are Ollama's own counts; local models ran on the `medium` profile (24 GB M5 Pro).

<picture><source media="(prefers-color-scheme: dark)" srcset="chart-dark.svg"><img alt="Cost, tasks solved and Claude tokens for Haiku, Sonnet and Opus across the three approaches" src="chart-light.svg"></picture>

## By Claude model

| Approach | Metric | Haiku 4.5 | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|---|
| Claude Code (agentic) | Tasks fully correct | 14/14 | 14/14 | 14/14 |
|  | Grader tests passed | 98/98 | 98/98 | 98/98 |
|  | Claude tokens | 9,199.3K | 1,425.9K | 2,197.9K |
|  | Claude output tokens | 136.3K | 29.7K | 43.3K |
|  | Claude cost (API prices) | $2.38 | $1.19 | $2.66 |
|  | Wall time | 21 min | 4 min | 7 min |
| Claude one-shot | Tasks fully correct | 12/14 | 14/14 | 14/14 |
|  | Grader tests passed | 91/98 | 98/98 | 98/98 |
|  | Claude tokens | 124.3K | 32.6K | 34.8K |
|  | Claude output tokens | 107.7K | 11.7K | 13.9K |
|  | Claude cost (API prices) | $0.56 | $0.20 | $0.45 |
|  | Wall time | 15 min | 2 min | 3 min |
| Hybrid | Tasks fully correct | 7/14 | 13/14 | 13/14 |
|  | Grader tests passed | 51/98 | 91/98 | 91/98 |
|  | Claude tokens | 598.2K | 193.1K | 224.0K |
|  | Claude output tokens | 388.9K | 67.1K | 83.3K |
|  | Claude cost (API prices) | $2.31 | $1.17 | $2.79 |
|  | Local tokens | 972.5K | 391.0K | 429.3K |
|  | Wall time | 175 min | 63 min | 49 min |

# Haiku 4.5


## Summary

| | Claude Code (agentic) | Claude one-shot | Hybrid (this repo) |
|---|---|---|---|
| Tasks fully correct | 14/14 | 12/14 | 7/14 |
| Grader tests passed | 98/98 | 91/98 | 51/98 |
| Claude tokens (total) | 9,199.3K | 124.3K | 598.2K |
| …of which new (not cache reads) | 529.6K | 124.3K | 590.0K |
| …of which Claude wrote (output) | 136.3K | 107.7K | 388.9K |
| Claude cost at API prices | $2.38 | $0.56 | $2.31 |
| Local tokens (free) | 0 | 0 | 972.5K |
| Wall time (sum) | 21 min | 15 min | 175 min |

**Hybrid vs. the others** (Claude cost at API prices, which weights output and cache reads correctly):

- vs Claude Code (agentic): saves 3% ($2.31 vs $2.38); Claude tokens 598.2K vs 9,199.3K
- vs Claude one-shot: costs 317% ($2.31 vs $0.56); Claude tokens 598.2K vs 124.3K

## Per task

Graders passed · Claude tokens (total / new) · cost · local tokens

| Task | Kind | Claude Code (agentic) | Claude one-shot | Hybrid (this repo) |
|---|---|---|---|---|
| `lru` | algorithm | ✅ 8/8 · 433.1K / 47.0K · $0.153 | ✅ 8/8 · 3.9K / 3.9K · $0.015 | ✅ 8/8 · 11.7K / 11.7K · $0.041 · 10.2K local |
| `dijkstra` | algorithm | ✅ 8/8 · 549.1K / 54.1K · $0.191 | ✅ 8/8 · 10.4K / 10.4K · $0.047 | ✅ 8/8 · 55.0K / 55.0K · $0.199 · 110.1K local |
| `roman` | parsing | ✅ 5/5 · 682.3K / 55.1K · $0.203 | ❌ 4/5 · 10.9K / 10.9K · $0.050 | ❌ 0/5 · 73.4K / 73.4K · $0.299 · 129.4K local |
| `intervals` | algorithm | ✅ 8/8 · 443.0K / 42.4K · $0.141 | ✅ 8/8 · 5.3K / 5.3K · $0.022 | ✅ 8/8 · 15.9K / 15.9K · $0.063 · 6.7K local |
| `toposort` | algorithm | ✅ 8/8 · 618.3K / 29.5K · $0.195 | ✅ 8/8 · 5.9K / 5.9K · $0.025 | ✅ 8/8 · 8.1K / 8.1K · $0.034 · 8.1K local |
| `levenshtein` | algorithm | ✅ 7/7 · 830.2K / 31.3K · $0.170 | ✅ 7/7 · 5.9K / 5.9K · $0.025 | ❌ 0/7 · 53.7K / 53.7K · $0.209 · 86.9K local |
| `calc` | parsing | ✅ 7/7 · 609.3K / 45.0K · $0.193 | ❌ 1/7 · 19.0K / 19.0K · $0.090 | ❌ 0/7 · 75.0K / 66.8K · $0.254 · 153.7K local |
| `knapsack` | algorithm | ✅ 7/7 · 320.5K / 23.2K · $0.098 | ✅ 7/7 · 9.6K / 9.6K · $0.043 | ❌ 0/7 · 65.8K / 65.8K · $0.269 · 83.5K local |
| `autocomplete` | data structure | ✅ 6/6 · 430.2K / 24.9K · $0.111 | ✅ 6/6 · 2.2K / 2.2K · $0.006 | ✅ 6/6 · 10.9K / 10.9K · $0.037 · 8.2K local |
| `duration` | parsing | ✅ 7/7 · 727.5K / 29.7K · $0.152 | ✅ 7/7 · 13.3K / 13.3K · $0.061 | ❌ 0/7 · 58.2K / 58.2K · $0.223 · 110.5K local |
| `justify` | text | ✅ 7/7 · 2,401.1K / 79.8K · $0.477 | ✅ 7/7 · 9.9K / 9.9K · $0.045 | ❌ 0/7 · 69.2K / 69.2K · $0.285 · 84.8K local |
| `rle` | text | ✅ 6/6 · 339.8K / 19.5K · $0.086 | ✅ 6/6 · 3.9K / 3.9K · $0.015 | ✅ 6/6 · 13.3K / 13.3K · $0.060 · 19.2K local |
| `matrix` | algorithm | ✅ 7/7 · 412.5K / 20.8K · $0.097 | ✅ 7/7 · 13.3K / 13.3K · $0.062 | ✅ 7/7 · 23.8K / 23.8K · $0.098 · 9.3K local |
| `sudoku` | algorithm | ✅ 7/7 · 402.4K / 27.3K · $0.116 | ✅ 7/7 · 10.9K / 10.9K · $0.050 | ❌ 0/7 · 64.2K / 64.2K · $0.242 · 152.0K local |

# Sonnet 5.5


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

# Opus 5.5


## Summary

| | Claude Code (agentic) | Claude one-shot | Hybrid (this repo) |
|---|---|---|---|
| Tasks fully correct | 14/14 | 14/14 | 13/14 |
| Grader tests passed | 98/98 | 98/98 | 91/98 |
| Claude tokens (total) | 2,197.9K | 34.8K | 224.0K |
| …of which new (not cache reads) | 217.5K | 34.8K | 224.0K |
| …of which Claude wrote (output) | 43.3K | 13.9K | 83.3K |
| Claude cost at API prices | $2.66 | $0.45 | $2.79 |
| Local tokens (free) | 0 | 0 | 429.3K |
| Wall time (sum) | 7 min | 3 min | 49 min |

**Hybrid vs. the others** (Claude cost at API prices, which weights output and cache reads correctly):

- vs Claude Code (agentic): costs 5% ($2.79 vs $2.66); Claude tokens 224.0K vs 2,197.9K
- vs Claude one-shot: costs 526% ($2.79 vs $0.45); Claude tokens 224.0K vs 34.8K

## Per task

Graders passed · Claude tokens (total / new) · cost · local tokens

| Task | Kind | Claude Code (agentic) | Claude one-shot | Hybrid (this repo) |
|---|---|---|---|---|
| `lru` | algorithm | ✅ 8/8 · 159.0K / 14.3K · $0.174 | ✅ 8/8 · 1.9K / 1.9K · $0.020 | ✅ 8/8 · 10.5K / 10.5K · $0.144 · 9.0K local |
| `dijkstra` | algorithm | ✅ 8/8 · 97.4K / 14.7K · $0.168 | ✅ 8/8 · 2.6K / 2.6K · $0.032 | ✅ 8/8 · 25.9K / 25.9K · $0.309 · 49.7K local |
| `roman` | parsing | ✅ 5/5 · 129.0K / 14.1K · $0.164 | ✅ 5/5 · 2.5K / 2.5K · $0.033 | ✅ 5/5 · 20.3K / 20.3K · $0.226 · 41.0K local |
| `intervals` | algorithm | ✅ 8/8 · 191.2K / 14.0K · $0.175 | ✅ 8/8 · 2.0K / 2.0K · $0.023 | ✅ 8/8 · 9.2K / 9.2K · $0.123 · 6.7K local |
| `toposort` | algorithm | ✅ 8/8 · 128.4K / 15.1K · $0.178 | ✅ 8/8 · 2.3K / 2.3K · $0.029 | ✅ 8/8 · 15.9K / 15.9K · $0.194 · 31.6K local |
| `levenshtein` | algorithm | ✅ 7/7 · 96.8K / 14.4K · $0.163 | ✅ 7/7 · 2.4K / 2.4K · $0.030 | ❌ 0/7 · 33.7K / 33.7K · $0.397 · 85.1K local |
| `calc` | parsing | ✅ 7/7 · 162.0K / 16.8K · $0.207 | ✅ 7/7 · 3.5K / 3.5K · $0.052 | ✅ 7/7 · 28.3K / 28.3K · $0.304 · 79.3K local |
| `knapsack` | algorithm | ✅ 7/7 · 161.1K / 15.7K · $0.193 | ✅ 7/7 · 2.7K / 2.7K · $0.036 | ✅ 7/7 · 12.6K / 12.6K · $0.173 · 25.8K local |
| `autocomplete` | data structure | ✅ 6/6 · 190.3K / 14.8K · $0.185 | ✅ 6/6 · 1.9K / 1.9K · $0.021 | ✅ 6/6 · 11.2K / 11.2K · $0.154 · 8.8K local |
| `duration` | parsing | ✅ 7/7 · 161.0K / 14.5K · $0.176 | ✅ 7/7 · 3.0K / 3.0K · $0.040 | ✅ 7/7 · 21.3K / 21.3K · $0.247 · 42.8K local |
| `justify` | text | ✅ 7/7 · 232.0K / 18.0K · $0.237 | ✅ 7/7 · 2.3K / 2.3K · $0.028 | ✅ 7/7 · 11.3K / 11.3K · $0.162 · 7.4K local |
| `rle` | text | ✅ 6/6 · 128.5K / 15.3K · $0.182 | ✅ 6/6 · 2.5K / 2.5K · $0.032 | ✅ 6/6 · 5.0K / 5.0K · $0.075 · 6.3K local |
| `matrix` | algorithm | ✅ 7/7 · 159.9K / 15.4K · $0.189 | ✅ 7/7 · 2.4K / 2.4K · $0.030 | ✅ 7/7 · 11.0K / 11.0K · $0.153 · 8.2K local |
| `sudoku` | algorithm | ✅ 7/7 · 201.3K / 20.4K · $0.263 | ✅ 7/7 · 2.8K / 2.8K · $0.038 | ✅ 7/7 · 7.8K / 7.8K · $0.130 · 27.9K local |
