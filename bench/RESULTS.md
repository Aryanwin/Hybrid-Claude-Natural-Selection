# Benchmark results

14 single-file tasks, each solved with each of three Claude models by six approaches: Claude Code working normally (agentic), one minimal Claude call (one-shot), the hybrid as first released (v1), with near-miss snippets and hidden-test disputes (v2), with the four cost cuts (v3), and auto mode (one lean call first, hybrid v3 only if that fails). Every result is scored by hidden grader tests (`bench/graders/`, verified against `bench/reference/`). Claude usage is exact (`claude -p --output-format json`); local tokens are Ollama's own counts; local models ran on the `medium` profile (24 GB M5 Pro).

<picture><source media="(prefers-color-scheme: dark)" srcset="chart-dark.svg"><img alt="Cost, tasks solved and Claude tokens for Haiku, Sonnet and Opus across six approaches" src="chart-light.svg"></picture>

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
| Hybrid v1 | Tasks fully correct | 7/14 | 13/14 | 13/14 |
|  | Grader tests passed | 51/98 | 91/98 | 91/98 |
|  | Claude tokens | 598.2K | 193.1K | 224.0K |
|  | Claude output tokens | 388.9K | 67.1K | 83.3K |
|  | Claude cost (API prices) | $2.31 | $1.17 | $2.79 |
|  | Local tokens | 972.5K | 391.0K | 429.3K |
|  | Wall time | 175 min | 63 min | 49 min |
| Hybrid v2 (+ near-miss, disputes) | Tasks fully correct | 11/14 | 14/14 | 14/14 |
|  | Grader tests passed | 77/98 | 98/98 | 98/98 |
|  | Claude tokens | 688.5K | 215.9K | 204.2K |
|  | Claude output tokens | 470.3K | 70.8K | 84.9K |
|  | Claude cost (API prices) | $2.72 | $1.29 | $2.65 |
|  | Local tokens | 838.3K | 409.8K | 332.2K |
|  | Wall time | 130 min | 78 min | 49 min |
| Hybrid v3 (+ cost cuts) | Tasks fully correct | 10/14 | 14/14 | 14/14 |
|  | Grader tests passed | 84/98 | 98/98 | 98/98 |
|  | Claude tokens | 378.3K | 112.5K | 126.6K |
|  | Claude output tokens | 280.0K | 41.3K | 49.5K |
|  | Claude cost (API prices) | $1.51 | $0.59 | $1.38 |
|  | Local tokens | 418.0K | 232.1K | 283.1K |
|  | Wall time | 76 min | 25 min | 54 min |
| Auto (one-shot first, then hybrid v3) | Tasks fully correct | 13/14 | 14/14 | 14/14 |
|  | Grader tests passed | 91/98 | 98/98 | 98/98 |
|  | Claude tokens | 434.1K | 46.2K | 51.6K |
|  | Claude output tokens | 331.4K | 17.7K | 23.2K |
|  | Claude cost (API prices) | $1.77 | $0.25 | $0.61 |
|  | Local tokens | 222.7K | 0 | 0 |
|  | Wall time | 66 min | 3 min | 4 min |

Auto mode's path per task: Sonnet and Opus solved all 14 with the single call; Haiku solved 10 that way and handed 4 to the hybrid.

Timing note: Haiku v2's `matrix` run was paused for ~22.5 minutes; that pause is subtracted from its wall time.

# Haiku 4.5


## Summary

| | Claude Code (agentic) | Claude one-shot | Hybrid v1 | Hybrid v2 (+ near-miss, disputes) | Hybrid v3 (+ cost cuts) | Auto (one-shot first, then hybrid v3) |
|---|---|---|---|---|---|---|
| Tasks fully correct | 14/14 | 12/14 | 7/14 | 11/14 | 10/14 | 13/14 |
| Grader tests passed | 98/98 | 91/98 | 51/98 | 77/98 | 84/98 | 91/98 |
| Claude tokens (total) | 9,199.3K | 124.3K | 598.2K | 688.5K | 378.3K | 434.1K |
| …of which new (not cache reads) | 529.6K | 124.3K | 590.0K | 688.5K | 378.3K | 434.1K |
| …of which Claude wrote (output) | 136.3K | 107.7K | 388.9K | 470.3K | 280.0K | 331.4K |
| Claude cost at API prices | $2.38 | $0.56 | $2.31 | $2.72 | $1.51 | $1.77 |
| Local tokens (free) | 0 | 0 | 972.5K | 838.3K | 418.0K | 222.7K |
| Wall time (sum) | 21 min | 15 min | 175 min | 130 min | 76 min | 66 min |

**Hybrid vs. the others** (Claude cost at API prices, which weights output and cache reads correctly):

- vs Claude Code (agentic): saves 3% ($2.31 vs $2.38); Claude tokens 598.2K vs 9,199.3K
- vs Claude one-shot: costs 317% ($2.31 vs $0.56); Claude tokens 598.2K vs 124.3K

## Per task

Graders passed · Claude tokens (total / new) · cost · local tokens

| Task | Kind | Claude Code (agentic) | Claude one-shot | Hybrid v1 | Hybrid v2 (+ near-miss, disputes) | Hybrid v3 (+ cost cuts) | Auto (one-shot first, then hybrid v3) |
|---|---|---|---|---|---|---|---|
| `lru` | algorithm | ✅ 8/8 · 433.1K / 47.0K · $0.153 | ✅ 8/8 · 3.9K / 3.9K · $0.015 | ✅ 8/8 · 11.7K / 11.7K · $0.041 · 10.2K local | ✅ 8/8 · 18.7K / 18.7K · $0.076 · 10.5K local | ✅ 8/8 · 14.6K / 14.6K · $0.066 · 5.5K local | ✅ 8/8 · 9.9K / 9.9K · $0.043 · 0 local |
| `dijkstra` | algorithm | ✅ 8/8 · 549.1K / 54.1K · $0.191 | ✅ 8/8 · 10.4K / 10.4K · $0.047 | ✅ 8/8 · 55.0K / 55.0K · $0.199 · 110.1K local | ✅ 8/8 · 55.2K / 55.2K · $0.225 · 85.9K local | ❌ 3/8 · 14.9K / 14.9K · $0.067 · 7.7K local | ✅ 8/8 · 17.4K / 17.4K · $0.081 · 0 local |
| `roman` | parsing | ✅ 5/5 · 682.3K / 55.1K · $0.203 | ❌ 4/5 · 10.9K / 10.9K · $0.050 | ❌ 0/5 · 73.4K / 73.4K · $0.299 · 129.4K local | ✅ 5/5 · 45.4K / 45.4K · $0.184 · 44.5K local | ❌ 4/5 · 16.9K / 16.9K · $0.061 · 7.9K local | ✅ 5/5 · 14.4K / 14.4K · $0.066 · 0 local |
| `intervals` | algorithm | ✅ 8/8 · 443.0K / 42.4K · $0.141 | ✅ 8/8 · 5.3K / 5.3K · $0.022 | ✅ 8/8 · 15.9K / 15.9K · $0.063 · 6.7K local | ✅ 8/8 · 19.7K / 19.7K · $0.065 · 17.3K local | ✅ 8/8 · 33.0K / 33.0K · $0.138 · 35.1K local | ✅ 8/8 · 7.9K / 7.9K · $0.034 · 0 local |
| `toposort` | algorithm | ✅ 8/8 · 618.3K / 29.5K · $0.195 | ✅ 8/8 · 5.9K / 5.9K · $0.025 | ✅ 8/8 · 8.1K / 8.1K · $0.034 · 8.1K local | ✅ 8/8 · 71.9K / 71.9K · $0.290 · 66.4K local | ✅ 8/8 · 45.4K / 45.4K · $0.184 · 28.2K local | ✅ 8/8 · 17.1K / 17.1K · $0.079 · 0 local |
| `levenshtein` | algorithm | ✅ 7/7 · 830.2K / 31.3K · $0.170 | ✅ 7/7 · 5.9K / 5.9K · $0.025 | ❌ 0/7 · 53.7K / 53.7K · $0.209 · 86.9K local | ✅ 7/7 · 26.3K / 26.3K · $0.095 · 9.3K local | ✅ 7/7 · 23.5K / 23.5K · $0.089 · 27.6K local | ✅ 7/7 · 10.6K / 10.6K · $0.047 · 0 local |
| `calc` | parsing | ✅ 7/7 · 609.3K / 45.0K · $0.193 | ❌ 1/7 · 19.0K / 19.0K · $0.090 | ❌ 0/7 · 75.0K / 66.8K · $0.254 · 153.7K local | ❌ 0/7 · 67.3K / 67.3K · $0.255 · 138.9K local | ❌ 0/7 · 30.8K / 30.8K · $0.117 · 110.8K local | ✅ 7/7 · 17.2K / 17.2K · $0.080 · 0 local |
| `knapsack` | algorithm | ✅ 7/7 · 320.5K / 23.2K · $0.098 | ✅ 7/7 · 9.6K / 9.6K · $0.043 | ❌ 0/7 · 65.8K / 65.8K · $0.269 · 83.5K local | ✅ 7/7 · 70.5K / 70.5K · $0.264 · 81.3K local | ✅ 7/7 · 23.5K / 23.5K · $0.088 · 36.9K local | ✅ 7/7 · 17.0K / 17.0K · $0.079 · 0 local |
| `autocomplete` | data structure | ✅ 6/6 · 430.2K / 24.9K · $0.111 | ✅ 6/6 · 2.2K / 2.2K · $0.006 | ✅ 6/6 · 10.9K / 10.9K · $0.037 · 8.2K local | ✅ 6/6 · 26.1K / 26.1K · $0.096 · 24.2K local | ✅ 6/6 · 9.5K / 9.5K · $0.040 · 5.0K local | ✅ 6/6 · 19.8K / 19.8K · $0.081 · 6.9K local |
| `duration` | parsing | ✅ 7/7 · 727.5K / 29.7K · $0.152 | ✅ 7/7 · 13.3K / 13.3K · $0.061 | ❌ 0/7 · 58.2K / 58.2K · $0.223 · 110.5K local | ❌ 0/7 · 65.5K / 65.5K · $0.250 · 88.8K local | ✅ 7/7 · 51.7K / 51.7K · $0.201 · 61.1K local | ✅ 7/7 · 83.0K / 83.0K · $0.326 · 49.3K local |
| `justify` | text | ✅ 7/7 · 2,401.1K / 79.8K · $0.477 | ✅ 7/7 · 9.9K / 9.9K · $0.045 | ❌ 0/7 · 69.2K / 69.2K · $0.285 · 84.8K local | ❌ 0/7 · 97.3K / 97.3K · $0.416 · 136.0K local | ✅ 7/7 · 78.9K / 78.9K · $0.322 · 58.1K local | ❌ 0/7 · 93.6K / 93.6K · $0.376 · 66.3K local |
| `rle` | text | ✅ 6/6 · 339.8K / 19.5K · $0.086 | ✅ 6/6 · 3.9K / 3.9K · $0.015 | ✅ 6/6 · 13.3K / 13.3K · $0.060 · 19.2K local | ✅ 6/6 · 13.2K / 13.2K · $0.060 · 9.3K local | ❌ 5/6 · 13.2K / 13.2K · $0.044 · 5.5K local | ✅ 6/6 · 11.6K / 11.6K · $0.051 · 0 local |
| `matrix` | algorithm | ✅ 7/7 · 412.5K / 20.8K · $0.097 | ✅ 7/7 · 13.3K / 13.3K · $0.062 | ✅ 7/7 · 23.8K / 23.8K · $0.098 · 9.3K local | ✅ 7/7 · 28.0K / 28.0K · $0.118 · 12.6K local | ✅ 7/7 · 6.5K / 6.5K · $0.026 · 5.6K local | ✅ 7/7 · 13.6K / 13.6K · $0.062 · 0 local |
| `sudoku` | algorithm | ✅ 7/7 · 402.4K / 27.3K · $0.116 | ✅ 7/7 · 10.9K / 10.9K · $0.050 | ❌ 0/7 · 64.2K / 64.2K · $0.242 · 152.0K local | ✅ 7/7 · 83.3K / 83.3K · $0.332 · 113.2K local | ✅ 7/7 · 15.9K / 15.9K · $0.072 · 23.2K local | ✅ 7/7 · 101.0K / 101.0K · $0.370 · 100.0K local |

# Sonnet 5.5


## Summary

| | Claude Code (agentic) | Claude one-shot | Hybrid v1 | Hybrid v2 (+ near-miss, disputes) | Hybrid v3 (+ cost cuts) | Auto (one-shot first, then hybrid v3) |
|---|---|---|---|---|---|---|
| Tasks fully correct | 14/14 | 14/14 | 13/14 | 14/14 | 14/14 | 14/14 |
| Grader tests passed | 98/98 | 98/98 | 91/98 | 98/98 | 98/98 | 98/98 |
| Claude tokens (total) | 1,425.9K | 32.6K | 193.1K | 215.9K | 112.5K | 46.2K |
| …of which new (not cache reads) | 191.4K | 32.6K | 193.1K | 215.9K | 110.7K | 46.2K |
| …of which Claude wrote (output) | 29.7K | 11.7K | 67.1K | 70.8K | 41.3K | 17.7K |
| Claude cost at API prices | $1.19 | $0.20 | $1.17 | $1.29 | $0.59 | $0.25 |
| Local tokens (free) | 0 | 0 | 391.0K | 409.8K | 232.1K | 0 |
| Wall time (sum) | 4 min | 2 min | 63 min | 78 min | 25 min | 3 min |

**Hybrid vs. the others** (Claude cost at API prices, which weights output and cache reads correctly):

- vs Claude Code (agentic): saves 1% ($1.17 vs $1.19); Claude tokens 193.1K vs 1,425.9K
- vs Claude one-shot: costs 486% ($1.17 vs $0.20); Claude tokens 193.1K vs 32.6K

## Per task

Graders passed · Claude tokens (total / new) · cost · local tokens

| Task | Kind | Claude Code (agentic) | Claude one-shot | Hybrid v1 | Hybrid v2 (+ near-miss, disputes) | Hybrid v3 (+ cost cuts) | Auto (one-shot first, then hybrid v3) |
|---|---|---|---|---|---|---|---|
| `lru` | algorithm | ✅ 8/8 · 95.8K / 12.4K · $0.076 | ✅ 8/8 · 1.8K / 1.8K · $0.009 | ✅ 8/8 · 9.8K / 9.8K · $0.065 · 8.7K local | ✅ 8/8 · 9.6K / 9.6K · $0.064 · 8.2K local | ✅ 8/8 · 4.2K / 4.2K · $0.025 · 5.8K local | ✅ 8/8 · 2.9K / 2.9K · $0.014 · 0 local |
| `dijkstra` | algorithm | ✅ 8/8 · 98.0K / 13.8K · $0.085 | ✅ 8/8 · 2.5K / 2.5K · $0.015 | ✅ 8/8 · 28.8K / 28.8K · $0.154 · 73.4K local | ✅ 8/8 · 8.3K / 8.3K · $0.070 · 13.4K local | ✅ 8/8 · 17.5K / 17.5K · $0.079 · 47.9K local | ✅ 8/8 · 3.5K / 3.5K · $0.019 · 0 local |
| `roman` | parsing | ✅ 5/5 · 130.1K / 14.1K · $0.092 | ✅ 5/5 · 2.6K / 2.6K · $0.017 | ✅ 5/5 · 20.1K / 20.1K · $0.113 · 33.8K local | ✅ 5/5 · 5.2K / 5.2K · $0.040 · 8.0K local | ✅ 5/5 · 4.4K / 4.4K · $0.026 · 7.6K local | ✅ 5/5 · 3.1K / 3.1K · $0.016 · 0 local |
| `intervals` | algorithm | ✅ 8/8 · 129.4K / 13.8K · $0.091 | ✅ 8/8 · 1.9K / 1.9K · $0.011 | ✅ 8/8 · 5.1K / 5.1K · $0.039 · 6.3K local | ✅ 8/8 · 8.5K / 8.5K · $0.054 · 7.2K local | ✅ 8/8 · 4.2K / 4.2K · $0.025 · 5.5K local | ✅ 8/8 · 2.8K / 2.8K · $0.013 · 0 local |
| `toposort` | algorithm | ✅ 8/8 · 96.1K / 12.6K · $0.077 | ✅ 8/8 · 1.9K / 1.9K · $0.011 | ✅ 8/8 · 5.7K / 5.7K · $0.045 · 6.4K local | ✅ 8/8 · 17.7K / 17.7K · $0.100 · 25.9K local | ✅ 8/8 · 19.0K / 17.2K · $0.068 · 49.7K local | ✅ 8/8 · 2.7K / 2.7K · $0.012 · 0 local |
| `levenshtein` | algorithm | ✅ 7/7 · 95.5K / 12.2K · $0.074 | ✅ 7/7 · 2.0K / 2.0K · $0.011 | ✅ 7/7 · 11.0K / 11.0K · $0.073 · 7.4K local | ✅ 7/7 · 10.2K / 10.2K · $0.067 · 8.5K local | ✅ 7/7 · 4.3K / 4.3K · $0.026 · 6.3K local | ✅ 7/7 · 2.8K / 2.8K · $0.013 · 0 local |
| `calc` | parsing | ✅ 7/7 · 97.2K / 14.9K · $0.092 | ✅ 7/7 · 3.1K / 3.1K · $0.022 | ❌ 0/7 · 37.0K / 37.0K · $0.184 · 136.2K local | ✅ 7/7 · 42.2K / 42.2K · $0.218 · 118.3K local | ✅ 7/7 · 6.0K / 6.0K · $0.043 · 9.5K local | ✅ 7/7 · 4.1K / 4.1K · $0.025 · 0 local |
| `knapsack` | algorithm | ✅ 7/7 · 97.6K / 13.6K · $0.084 | ✅ 7/7 · 2.3K / 2.3K · $0.014 | ✅ 7/7 · 10.6K / 10.6K · $0.070 · 27.1K local | ✅ 7/7 · 5.9K / 5.9K · $0.047 · 9.1K local | ✅ 7/7 · 6.1K / 6.1K · $0.044 · 7.6K local | ✅ 7/7 · 3.4K / 3.4K · $0.019 · 0 local |
| `autocomplete` | data structure | ✅ 6/6 · 127.6K / 13.2K · $0.087 | ✅ 6/6 · 1.9K / 1.9K · $0.010 | ✅ 6/6 · 9.9K / 9.9K · $0.065 · 7.8K local | ✅ 6/6 · 9.9K / 9.9K · $0.065 · 8.3K local | ✅ 6/6 · 4.6K / 4.6K · $0.028 · 6.2K local | ✅ 6/6 · 2.9K / 2.9K · $0.014 · 0 local |
| `duration` | parsing | ✅ 7/7 · 97.7K / 13.5K · $0.083 | ✅ 7/7 · 2.6K / 2.6K · $0.016 | ✅ 7/7 · 11.1K / 11.1K · $0.071 · 9.0K local | ✅ 7/7 · 18.2K / 18.2K · $0.101 · 46.5K local | ✅ 7/7 · 5.3K / 5.3K · $0.035 · 7.7K local | ✅ 7/7 · 3.6K / 3.6K · $0.021 · 0 local |
| `justify` | text | ✅ 7/7 · 131.8K / 15.4K · $0.100 | ✅ 7/7 · 2.3K / 2.3K · $0.014 | ✅ 7/7 · 10.3K / 10.3K · $0.067 · 6.5K local | ✅ 7/7 · 10.0K / 10.0K · $0.066 · 6.7K local | ✅ 7/7 · 13.3K / 13.3K · $0.061 · 29.4K local | ✅ 7/7 · 3.3K / 3.3K · $0.018 · 0 local |
| `rle` | text | ✅ 6/6 · 97.9K / 13.8K · $0.086 | ✅ 6/6 · 2.7K / 2.7K · $0.018 | ✅ 6/6 · 19.6K / 19.6K · $0.114 · 31.9K local | ✅ 6/6 · 13.4K / 13.4K · $0.079 · 25.2K local | ✅ 6/6 · 12.7K / 12.7K · $0.051 · 32.2K local | ✅ 6/6 · 3.2K / 3.2K · $0.017 · 0 local |
| `matrix` | algorithm | ✅ 7/7 · 64.6K / 13.0K · $0.074 | ✅ 7/7 · 2.1K / 2.1K · $0.013 | ✅ 7/7 · 6.6K / 6.6K · $0.054 · 8.5K local | ✅ 7/7 · 11.9K / 11.9K · $0.078 · 9.5K local | ✅ 7/7 · 4.9K / 4.9K · $0.032 · 7.1K local | ✅ 7/7 · 3.1K / 3.1K · $0.016 · 0 local |
| `sudoku` | algorithm | ✅ 7/7 · 66.7K / 15.2K · $0.089 | ✅ 7/7 · 2.8K / 2.8K · $0.019 | ✅ 7/7 · 7.5K / 7.5K · $0.063 · 28.0K local | ✅ 7/7 · 44.9K / 44.9K · $0.241 · 115.0K local | ✅ 7/7 · 5.9K / 5.9K · $0.042 · 9.4K local | ✅ 7/7 · 4.7K / 4.7K · $0.031 · 0 local |

# Opus 5.5


## Summary

| | Claude Code (agentic) | Claude one-shot | Hybrid v1 | Hybrid v2 (+ near-miss, disputes) | Hybrid v3 (+ cost cuts) | Auto (one-shot first, then hybrid v3) |
|---|---|---|---|---|---|---|
| Tasks fully correct | 14/14 | 14/14 | 13/14 | 14/14 | 14/14 | 14/14 |
| Grader tests passed | 98/98 | 98/98 | 91/98 | 98/98 | 98/98 | 98/98 |
| Claude tokens (total) | 2,197.9K | 34.8K | 224.0K | 204.2K | 126.6K | 51.6K |
| …of which new (not cache reads) | 217.5K | 34.8K | 224.0K | 204.2K | 126.6K | 51.6K |
| …of which Claude wrote (output) | 43.3K | 13.9K | 83.3K | 84.9K | 49.5K | 23.2K |
| Claude cost at API prices | $2.66 | $0.45 | $2.79 | $2.65 | $1.38 | $0.61 |
| Local tokens (free) | 0 | 0 | 429.3K | 332.2K | 283.1K | 0 |
| Wall time (sum) | 7 min | 3 min | 49 min | 49 min | 54 min | 4 min |

**Hybrid vs. the others** (Claude cost at API prices, which weights output and cache reads correctly):

- vs Claude Code (agentic): costs 5% ($2.79 vs $2.66); Claude tokens 224.0K vs 2,197.9K
- vs Claude one-shot: costs 526% ($2.79 vs $0.45); Claude tokens 224.0K vs 34.8K

## Per task

Graders passed · Claude tokens (total / new) · cost · local tokens

| Task | Kind | Claude Code (agentic) | Claude one-shot | Hybrid v1 | Hybrid v2 (+ near-miss, disputes) | Hybrid v3 (+ cost cuts) | Auto (one-shot first, then hybrid v3) |
|---|---|---|---|---|---|---|---|
| `lru` | algorithm | ✅ 8/8 · 159.0K / 14.3K · $0.174 | ✅ 8/8 · 1.9K / 1.9K · $0.020 | ✅ 8/8 · 10.5K / 10.5K · $0.144 · 9.0K local | ✅ 8/8 · 10.6K / 10.6K · $0.145 · 8.9K local | ✅ 8/8 · 5.1K / 5.1K · $0.068 · 5.7K local | ✅ 8/8 · 3.1K / 3.1K · $0.031 · 0 local |
| `dijkstra` | algorithm | ✅ 8/8 · 97.4K / 14.7K · $0.168 | ✅ 8/8 · 2.6K / 2.6K · $0.032 | ✅ 8/8 · 25.9K / 25.9K · $0.309 · 49.7K local | ✅ 8/8 · 24.0K / 24.0K · $0.280 · 51.5K local | ✅ 8/8 · 17.3K / 17.3K · $0.156 · 49.5K local | ✅ 8/8 · 3.7K / 3.7K · $0.042 · 0 local |
| `roman` | parsing | ✅ 5/5 · 129.0K / 14.1K · $0.164 | ✅ 5/5 · 2.5K / 2.5K · $0.033 | ✅ 5/5 · 20.3K / 20.3K · $0.226 · 41.0K local | ✅ 5/5 · 6.2K / 6.2K · $0.100 · 9.7K local | ✅ 5/5 · 4.8K / 4.8K · $0.061 · 6.8K local | ✅ 5/5 · 3.6K / 3.6K · $0.042 · 0 local |
| `intervals` | algorithm | ✅ 8/8 · 191.2K / 14.0K · $0.175 | ✅ 8/8 · 2.0K / 2.0K · $0.023 | ✅ 8/8 · 9.2K / 9.2K · $0.123 · 6.7K local | ✅ 8/8 · 9.0K / 9.0K · $0.118 · 6.7K local | ✅ 8/8 · 4.8K / 4.8K · $0.062 · 14.1K local | ✅ 8/8 · 2.9K / 2.9K · $0.028 · 0 local |
| `toposort` | algorithm | ✅ 8/8 · 128.4K / 15.1K · $0.178 | ✅ 8/8 · 2.3K / 2.3K · $0.029 | ✅ 8/8 · 15.9K / 15.9K · $0.194 · 31.6K local | ✅ 8/8 · 16.0K / 16.0K · $0.197 · 31.6K local | ✅ 8/8 · 5.2K / 5.2K · $0.070 · 6.1K local | ✅ 8/8 · 3.4K / 3.4K · $0.038 · 0 local |
| `levenshtein` | algorithm | ✅ 7/7 · 96.8K / 14.4K · $0.163 | ✅ 7/7 · 2.4K / 2.4K · $0.030 | ❌ 0/7 · 33.7K / 33.7K · $0.397 · 85.1K local | ✅ 7/7 · 11.6K / 11.6K · $0.162 · 8.1K local | ✅ 7/7 · 5.6K / 5.6K · $0.078 · 6.3K local | ✅ 7/7 · 3.7K / 3.7K · $0.044 · 0 local |
| `calc` | parsing | ✅ 7/7 · 162.0K / 16.8K · $0.207 | ✅ 7/7 · 3.5K / 3.5K · $0.052 | ✅ 7/7 · 28.3K / 28.3K · $0.304 · 79.3K local | ✅ 7/7 · 35.8K / 35.8K · $0.390 · 82.7K local | ✅ 7/7 · 17.2K / 17.2K · $0.152 · 101.0K local | ✅ 7/7 · 4.7K / 4.7K · $0.063 · 0 local |
| `knapsack` | algorithm | ✅ 7/7 · 161.1K / 15.7K · $0.193 | ✅ 7/7 · 2.7K / 2.7K · $0.036 | ✅ 7/7 · 12.6K / 12.6K · $0.173 · 25.8K local | ✅ 7/7 · 9.5K / 9.5K · $0.166 · 10.4K local | ✅ 7/7 · 6.0K / 6.0K · $0.085 · 7.5K local | ✅ 7/7 · 3.8K / 3.8K · $0.046 · 0 local |
| `autocomplete` | data structure | ✅ 6/6 · 190.3K / 14.8K · $0.185 | ✅ 6/6 · 1.9K / 1.9K · $0.021 | ✅ 6/6 · 11.2K / 11.2K · $0.154 · 8.8K local | ✅ 6/6 · 18.9K / 18.9K · $0.246 · 8.9K local | ✅ 6/6 · 11.5K / 11.5K · $0.122 · 5.6K local | ✅ 6/6 · 3.2K / 3.2K · $0.034 · 0 local |
| `duration` | parsing | ✅ 7/7 · 161.0K / 14.5K · $0.176 | ✅ 7/7 · 3.0K / 3.0K · $0.040 | ✅ 7/7 · 21.3K / 21.3K · $0.247 · 42.8K local | ✅ 7/7 · 18.1K / 18.1K · $0.223 · 41.5K local | ✅ 7/7 · 5.3K / 5.3K · $0.070 · 7.3K local | ✅ 7/7 · 4.0K / 4.0K · $0.048 · 0 local |
| `justify` | text | ✅ 7/7 · 232.0K / 18.0K · $0.237 | ✅ 7/7 · 2.3K / 2.3K · $0.028 | ✅ 7/7 · 11.3K / 11.3K · $0.162 · 7.4K local | ✅ 7/7 · 11.3K / 11.3K · $0.160 · 7.5K local | ✅ 7/7 · 5.8K / 5.8K · $0.081 · 6.2K local | ✅ 7/7 · 3.3K / 3.3K · $0.035 · 0 local |
| `rle` | text | ✅ 6/6 · 128.5K / 15.3K · $0.182 | ✅ 6/6 · 2.5K / 2.5K · $0.032 | ✅ 6/6 · 5.0K / 5.0K · $0.075 · 6.3K local | ✅ 6/6 · 4.8K / 4.8K · $0.071 · 6.5K local | ✅ 6/6 · 13.5K / 13.5K · $0.120 · 39.2K local | ✅ 6/6 · 3.5K / 3.5K · $0.039 · 0 local |
| `matrix` | algorithm | ✅ 7/7 · 159.9K / 15.4K · $0.189 | ✅ 7/7 · 2.4K / 2.4K · $0.030 | ✅ 7/7 · 11.0K / 11.0K · $0.153 · 8.2K local | ✅ 7/7 · 7.5K / 7.5K · $0.126 · 24.9K local | ✅ 7/7 · 5.9K / 5.9K · $0.083 · 7.0K local | ✅ 7/7 · 3.6K / 3.6K · $0.041 · 0 local |
| `sudoku` | algorithm | ✅ 7/7 · 201.3K / 20.4K · $0.263 | ✅ 7/7 · 2.8K / 2.8K · $0.038 | ✅ 7/7 · 7.8K / 7.8K · $0.130 · 27.9K local | ✅ 7/7 · 20.9K / 20.9K · $0.269 · 33.4K local | ✅ 7/7 · 18.6K / 18.6K · $0.168 · 20.8K local | ✅ 7/7 · 5.2K / 5.2K · $0.073 · 0 local |
