# Agreement report

agenteval 0.1.0


Judges with several runs (_r2, _r3 ...) are pooled: each run of each trajectory counts as an item. Brackets are 95% bootstrap intervals (2000 resamples of the trajectories; all runs and criteria of a drawn trajectory move together). kappa_w is quadratic-weighted Cohen's kappa. Run-to-run is the mean kappa_w between pairs of a judge's own runs. See GOLD_CONFLICTS.md before reading agreement with gold.

## Summary: simulated set

| Rater | runs | vs gold exact | vs gold kappa_w | vs human exact | vs human kappa_w | run-to-run kappa_w | mean total (0-14) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Human | 1 | 0.80 [0.75, 0.85] | 0.80 [0.75, 0.85] | — | — | — | 8.56 |
| Fable-5.1 (corpus) | 3 | 0.85 [0.80, 0.89] | 0.88 [0.85, 0.92] | 0.86 [0.82, 0.90] | 0.85 [0.80, 0.90] | 0.97 | 8.91 |
| Gemini-3-Flash (corpus) | 3 | 0.87 [0.83, 0.91] | 0.89 [0.86, 0.93] | 0.89 [0.85, 0.93] | 0.86 [0.80, 0.92] | 0.98 | 8.83 |
| Haiku-5.5 (corpus) | 3 | 0.86 [0.82, 0.90] | 0.88 [0.83, 0.92] | 0.88 [0.84, 0.91] | 0.85 [0.78, 0.90] | 0.96 | 8.67 |
| Opus-5.5 (corpus) | 3 | 0.84 [0.80, 0.89] | 0.88 [0.84, 0.91] | 0.86 [0.82, 0.89] | 0.83 [0.78, 0.88] | 0.93 | 8.87 |
| Sonnet-5.5 (corpus) | 3 | 0.88 [0.85, 0.91] | 0.90 [0.87, 0.93] | 0.82 [0.78, 0.85] | 0.79 [0.73, 0.83] | 0.95 | 8.79 |

Gold mean total: 8.84

## Run-to-run stability

| Judge | runs | kappa_w vs gold, by run | pairwise exact | pairwise kappa_w | cells identical in every run |
| --- | --- | --- | --- | --- | --- |
| Fable-5.1 (corpus) | 3 | 0.89, 0.90, 0.87 | 0.94 | 0.97 | 0.92 |
| Gemini-3-Flash (corpus) | 3 | 0.89, 0.90, 0.89 | 0.98 | 0.98 | 0.97 |
| Haiku-5.5 (corpus) | 3 | 0.89, 0.88, 0.87 | 0.95 | 0.96 | 0.93 |
| Opus-5.5 (corpus) | 3 | 0.87, 0.90, 0.86 | 0.94 | 0.93 | 0.91 |
| Sonnet-5.5 (corpus) | 3 | 0.91, 0.91, 0.89 | 0.93 | 0.95 | 0.90 |

## Human vs ground truth (simulated set)
n = 50 trajectories; diff = human minus gold

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.86 | 0.98 | 0.88 | +0.12 |
| C2 | 0.78 | 0.86 | 0.64 | -0.36 |
| C3 | 0.78 | 0.90 | 0.70 | -0.24 |
| C4 | 0.78 | 0.94 | 0.78 | +0.08 |
| C5 | 0.74 | 1.00 | 0.85 | +0.22 |
| C6 | 0.86 | 0.98 | 0.84 | -0.16 |
| C7 | 0.82 | 1.00 | 0.81 | +0.06 |
| **pooled** | 0.80 | 0.95 | 0.80 | -0.04 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 42 | 0.86 | 0.91 | +0.14 |
| clean | 56 | 0.93 | 0.00 | -0.12 |
| loop | 42 | 0.90 | 0.74 | -0.17 |
| premature_termination | 42 | 0.93 | 0.93 | +0.10 |
| stale_context | 42 | 0.90 | 0.84 | +0.17 |
| tool_error_ignored | 42 | 0.71 | 0.62 | -0.36 |
| unsupported_claim | 42 | 0.60 | 0.45 | +0.05 |
| wrong_tool | 42 | 0.55 | 0.35 | -0.10 |

Mean total score (0-14): human 8.56, gold 8.84

## Judge [Fable-5.1 (corpus)] vs ground truth
n = 50 trajectories x 3 runs, pooled; diff = judge minus gold

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.66 | 1.00 | 0.80 | +0.34 |
| C2 | 0.93 | 0.99 | 0.94 | -0.08 |
| C3 | 0.78 | 0.90 | 0.71 | -0.32 |
| C4 | 1.00 | 1.00 | 1.00 | +0.00 |
| C5 | 0.83 | 1.00 | 0.91 | +0.15 |
| C6 | 0.88 | 1.00 | 0.90 | -0.12 |
| C7 | 0.86 | 1.00 | 0.85 | +0.10 |
| **pooled** | 0.85 | 0.98 | 0.88 | +0.01 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.88 | 0.92 | +0.12 |
| clean | 168 | 1.00 | 1.00 | +0.00 |
| loop | 126 | 1.00 | 1.00 | +0.00 |
| premature_termination | 126 | 0.95 | 0.98 | +0.05 |
| stale_context | 126 | 0.93 | 0.95 | -0.03 |
| tool_error_ignored | 126 | 0.72 | 0.63 | -0.22 |
| unsupported_claim | 126 | 0.76 | 0.72 | +0.24 |
| wrong_tool | 126 | 0.49 | 0.34 | -0.06 |

Mean total score (0-14): judge 8.91, gold 8.84

## Judge [Fable-5.1 (corpus)] vs human (simulated set)
n = 50 trajectories x 3 runs, pooled; diff = judge minus human

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.72 | 0.98 | 0.81 | +0.22 |
| C2 | 0.78 | 0.86 | 0.63 | +0.28 |
| C3 | 0.96 | 0.96 | 0.92 | -0.08 |
| C4 | 0.78 | 0.94 | 0.78 | -0.08 |
| C5 | 0.89 | 1.00 | 0.94 | -0.07 |
| C6 | 0.98 | 0.98 | 0.95 | +0.04 |
| C7 | 0.92 | 1.00 | 0.91 | +0.04 |
| **pooled** | 0.86 | 0.96 | 0.85 | +0.05 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.93 | 0.95 | -0.02 |
| clean | 168 | 0.93 | 0.00 | +0.12 |
| loop | 126 | 0.90 | 0.74 | +0.17 |
| premature_termination | 126 | 0.88 | 0.90 | -0.05 |
| stale_context | 126 | 0.86 | 0.83 | -0.20 |
| tool_error_ignored | 126 | 0.71 | 0.69 | +0.13 |
| unsupported_claim | 126 | 0.76 | 0.38 | +0.19 |
| wrong_tool | 126 | 0.90 | 0.84 | +0.03 |

Mean total score (0-14): judge 8.91, human 8.56

### Largest judge-vs-gold disagreements [Fable-5.1 (corpus)] (gap of 2)

| tid | mode | criterion | judge, by run | gold | runs with gap 2 |
| --- | --- | --- | --- | --- | --- |
| S13 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S17 | stale_context | C2 | 0, 2, 1 | 2 | 1 of 3 |
| S18 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S26 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S30 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S50 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |

## Judge [Gemini-3-Flash (corpus)] vs ground truth
n = 50 trajectories x 3 runs, pooled; diff = judge minus gold

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.85 | 1.00 | 0.91 | +0.15 |
| C2 | 0.96 | 0.98 | 0.93 | -0.06 |
| C3 | 0.77 | 0.89 | 0.70 | -0.31 |
| C4 | 0.99 | 1.00 | 1.00 | +0.01 |
| C5 | 0.76 | 0.99 | 0.85 | +0.22 |
| C6 | 0.88 | 1.00 | 0.90 | -0.12 |
| C7 | 0.87 | 1.00 | 0.85 | +0.09 |
| **pooled** | 0.87 | 0.98 | 0.89 | -0.00 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.85 | 0.91 | +0.15 |
| clean | 168 | 1.00 | 1.00 | +0.00 |
| loop | 126 | 0.98 | 0.98 | -0.02 |
| premature_termination | 126 | 1.00 | 1.00 | +0.00 |
| stale_context | 126 | 0.90 | 0.89 | -0.04 |
| tool_error_ignored | 126 | 0.87 | 0.74 | -0.24 |
| unsupported_claim | 126 | 0.72 | 0.63 | +0.28 |
| wrong_tool | 126 | 0.58 | 0.43 | -0.15 |

Mean total score (0-14): judge 8.83, gold 8.84

## Judge [Gemini-3-Flash (corpus)] vs human (simulated set)
n = 50 trajectories x 3 runs, pooled; diff = judge minus human

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.91 | 0.98 | 0.92 | +0.03 |
| C2 | 0.75 | 0.84 | 0.59 | +0.30 |
| C3 | 0.95 | 0.95 | 0.91 | -0.07 |
| C4 | 0.77 | 0.94 | 0.78 | -0.07 |
| C5 | 0.97 | 0.99 | 0.97 | +0.00 |
| C6 | 0.98 | 0.98 | 0.95 | +0.04 |
| C7 | 0.91 | 1.00 | 0.90 | +0.03 |
| **pooled** | 0.89 | 0.96 | 0.86 | +0.04 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.99 | 1.00 | +0.01 |
| clean | 168 | 0.93 | 0.00 | +0.12 |
| loop | 126 | 0.90 | 0.74 | +0.15 |
| premature_termination | 126 | 0.93 | 0.93 | -0.10 |
| stale_context | 126 | 0.83 | 0.77 | -0.21 |
| tool_error_ignored | 126 | 0.77 | 0.74 | +0.12 |
| unsupported_claim | 126 | 0.80 | 0.35 | +0.23 |
| wrong_tool | 126 | 0.97 | 0.90 | -0.06 |

Mean total score (0-14): judge 8.83, human 8.56

### Largest judge-vs-gold disagreements [Gemini-3-Flash (corpus)] (gap of 2)

| tid | mode | criterion | judge, by run | gold | runs with gap 2 |
| --- | --- | --- | --- | --- | --- |
| S13 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S17 | stale_context | C2 | 0, 0, 0 | 2 | 3 of 3 |
| S17 | stale_context | C3 | 0, 0, 2 | 0 | 1 of 3 |
| S17 | stale_context | C5 | 0, 2, 2 | 2 | 1 of 3 |
| S18 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S26 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S30 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S50 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |

## Judge [Haiku-5.5 (corpus)] vs ground truth
n = 50 trajectories x 3 runs, pooled; diff = judge minus gold

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.83 | 0.99 | 0.89 | +0.17 |
| C2 | 0.91 | 0.98 | 0.90 | -0.11 |
| C3 | 0.77 | 0.89 | 0.70 | -0.31 |
| C4 | 1.00 | 1.00 | 1.00 | +0.00 |
| C5 | 0.78 | 0.97 | 0.83 | +0.10 |
| C6 | 0.88 | 1.00 | 0.90 | -0.12 |
| C7 | 0.86 | 0.99 | 0.81 | +0.09 |
| **pooled** | 0.86 | 0.98 | 0.88 | -0.02 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.84 | 0.87 | +0.13 |
| clean | 168 | 1.00 | 1.00 | +0.00 |
| loop | 126 | 0.95 | 0.95 | -0.05 |
| premature_termination | 126 | 1.00 | 1.00 | +0.00 |
| stale_context | 126 | 0.89 | 0.83 | -0.13 |
| tool_error_ignored | 126 | 0.86 | 0.73 | -0.26 |
| unsupported_claim | 126 | 0.75 | 0.68 | +0.25 |
| wrong_tool | 126 | 0.57 | 0.43 | -0.14 |

Mean total score (0-14): judge 8.67, gold 8.84

## Judge [Haiku-5.5 (corpus)] vs human (simulated set)
n = 50 trajectories x 3 runs, pooled; diff = judge minus human

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.89 | 0.97 | 0.90 | +0.05 |
| C2 | 0.74 | 0.86 | 0.60 | +0.25 |
| C3 | 0.95 | 0.95 | 0.91 | -0.07 |
| C4 | 0.78 | 0.94 | 0.78 | -0.08 |
| C5 | 0.89 | 0.95 | 0.85 | -0.12 |
| C6 | 0.98 | 0.98 | 0.95 | +0.04 |
| C7 | 0.92 | 0.99 | 0.87 | +0.03 |
| **pooled** | 0.88 | 0.95 | 0.85 | +0.02 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.91 | 0.87 | -0.02 |
| clean | 168 | 0.93 | 0.00 | +0.12 |
| loop | 126 | 0.89 | 0.77 | +0.12 |
| premature_termination | 126 | 0.93 | 0.93 | -0.10 |
| stale_context | 126 | 0.82 | 0.72 | -0.30 |
| tool_error_ignored | 126 | 0.79 | 0.76 | +0.10 |
| unsupported_claim | 126 | 0.78 | 0.37 | +0.21 |
| wrong_tool | 126 | 0.98 | 0.91 | -0.05 |

Mean total score (0-14): judge 8.67, human 8.56

### Largest judge-vs-gold disagreements [Haiku-5.5 (corpus)] (gap of 2)

| tid | mode | criterion | judge, by run | gold | runs with gap 2 |
| --- | --- | --- | --- | --- | --- |
| S12 | stale_context | C5 | 2, 2, 0 | 2 | 1 of 3 |
| S13 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S17 | stale_context | C2 | 0, 0, 0 | 2 | 3 of 3 |
| S17 | stale_context | C5 | 0, 0, 0 | 2 | 3 of 3 |
| S17 | stale_context | C7 | 0, 1, 0 | 2 | 2 of 3 |
| S18 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S23 | arithmetic_error | C1 | 0, 2, 0 | 0 | 1 of 3 |
| S23 | arithmetic_error | C3 | 0, 2, 0 | 0 | 1 of 3 |
| S26 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S30 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S50 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |

## Judge [Opus-5.5 (corpus)] vs ground truth
n = 50 trajectories x 3 runs, pooled; diff = judge minus gold

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.65 | 1.00 | 0.79 | +0.35 |
| C2 | 0.96 | 1.00 | 0.97 | -0.04 |
| C3 | 0.78 | 0.90 | 0.71 | -0.32 |
| C4 | 1.00 | 1.00 | 1.00 | +0.00 |
| C5 | 0.76 | 0.96 | 0.80 | +0.04 |
| C6 | 0.88 | 1.00 | 0.90 | -0.12 |
| C7 | 0.88 | 1.00 | 0.87 | +0.12 |
| **pooled** | 0.84 | 0.98 | 0.88 | +0.00 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.83 | 0.90 | +0.07 |
| clean | 168 | 1.00 | 1.00 | +0.00 |
| loop | 126 | 1.00 | 1.00 | +0.00 |
| premature_termination | 126 | 0.95 | 0.98 | +0.05 |
| stale_context | 126 | 0.93 | 0.89 | -0.07 |
| tool_error_ignored | 126 | 0.74 | 0.65 | -0.19 |
| unsupported_claim | 126 | 0.76 | 0.72 | +0.24 |
| wrong_tool | 126 | 0.49 | 0.34 | -0.06 |

Mean total score (0-14): judge 8.87, gold 8.84

## Judge [Opus-5.5 (corpus)] vs human (simulated set)
n = 50 trajectories x 3 runs, pooled; diff = judge minus human

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.71 | 0.98 | 0.80 | +0.23 |
| C2 | 0.79 | 0.87 | 0.64 | +0.32 |
| C3 | 0.96 | 0.96 | 0.92 | -0.08 |
| C4 | 0.78 | 0.94 | 0.78 | -0.08 |
| C5 | 0.86 | 0.92 | 0.79 | -0.18 |
| C6 | 0.98 | 0.98 | 0.95 | +0.04 |
| C7 | 0.94 | 1.00 | 0.93 | +0.06 |
| **pooled** | 0.86 | 0.95 | 0.83 | +0.04 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.93 | 0.87 | -0.07 |
| clean | 168 | 0.93 | 0.00 | +0.12 |
| loop | 126 | 0.90 | 0.74 | +0.17 |
| premature_termination | 126 | 0.88 | 0.90 | -0.05 |
| stale_context | 126 | 0.86 | 0.78 | -0.24 |
| tool_error_ignored | 126 | 0.70 | 0.69 | +0.17 |
| unsupported_claim | 126 | 0.76 | 0.38 | +0.19 |
| wrong_tool | 126 | 0.90 | 0.84 | +0.03 |

Mean total score (0-14): judge 8.87, human 8.56

### Largest judge-vs-gold disagreements [Opus-5.5 (corpus)] (gap of 2)

| tid | mode | criterion | judge, by run | gold | runs with gap 2 |
| --- | --- | --- | --- | --- | --- |
| S09 | stale_context | C5 | 2, 2, 0 | 2 | 1 of 3 |
| S10 | stale_context | C5 | 2, 2, 0 | 2 | 1 of 3 |
| S12 | stale_context | C5 | 2, 2, 0 | 2 | 1 of 3 |
| S13 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S17 | stale_context | C5 | 2, 2, 0 | 2 | 1 of 3 |
| S18 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S26 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S30 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |
| S35 | stale_context | C5 | 2, 2, 0 | 2 | 1 of 3 |
| S40 | stale_context | C5 | 2, 2, 0 | 2 | 1 of 3 |
| S50 | tool_error_ignored | C3 | 0, 0, 0 | 2 | 3 of 3 |

## Judge [Sonnet-5.5 (corpus)] vs ground truth
n = 50 trajectories x 3 runs, pooled; diff = judge minus gold

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.90 | 0.99 | 0.93 | +0.11 |
| C2 | 0.99 | 0.99 | 0.98 | -0.01 |
| C3 | 0.75 | 0.91 | 0.64 | +0.07 |
| C4 | 1.00 | 1.00 | 1.00 | +0.00 |
| C5 | 0.80 | 1.00 | 0.89 | +0.07 |
| C6 | 0.88 | 1.00 | 0.90 | -0.12 |
| C7 | 0.85 | 1.00 | 0.84 | -0.15 |
| **pooled** | 0.88 | 0.98 | 0.90 | -0.01 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.71 | 0.58 | +0.40 |
| clean | 168 | 1.00 | 1.00 | +0.00 |
| loop | 126 | 1.00 | 1.00 | +0.00 |
| premature_termination | 126 | 0.90 | 0.95 | -0.10 |
| stale_context | 126 | 0.88 | 0.91 | -0.10 |
| tool_error_ignored | 126 | 0.91 | 0.94 | -0.08 |
| unsupported_claim | 126 | 0.90 | 0.90 | +0.10 |
| wrong_tool | 126 | 0.71 | 0.35 | -0.28 |

Mean total score (0-14): judge 8.79, gold 8.84

## Judge [Sonnet-5.5 (corpus)] vs human (simulated set)
n = 50 trajectories x 3 runs, pooled; diff = judge minus human

| Criterion | exact | within 1 | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| C1 | 0.89 | 0.97 | 0.90 | -0.01 |
| C2 | 0.77 | 0.85 | 0.62 | +0.35 |
| C3 | 0.77 | 0.81 | 0.55 | +0.31 |
| C4 | 0.78 | 0.94 | 0.78 | -0.08 |
| C5 | 0.81 | 1.00 | 0.89 | -0.15 |
| C6 | 0.98 | 0.98 | 0.95 | +0.04 |
| C7 | 0.72 | 1.00 | 0.72 | -0.21 |
| **pooled** | 0.82 | 0.94 | 0.79 | +0.03 |

| Group | n items | exact | kappa_w | mean diff |
| --- | --- | --- | --- | --- |
| arithmetic_error | 126 | 0.85 | 0.66 | +0.25 |
| clean | 168 | 0.93 | 0.00 | +0.12 |
| loop | 126 | 0.90 | 0.74 | +0.17 |
| premature_termination | 126 | 0.83 | 0.87 | -0.19 |
| stale_context | 126 | 0.80 | 0.78 | -0.27 |
| tool_error_ignored | 126 | 0.69 | 0.55 | +0.28 |
| unsupported_claim | 126 | 0.67 | 0.44 | +0.06 |
| wrong_tool | 126 | 0.83 | 0.66 | -0.18 |

Mean total score (0-14): judge 8.79, human 8.56

### Largest judge-vs-gold disagreements [Sonnet-5.5 (corpus)] (gap of 2)

| tid | mode | criterion | judge, by run | gold | runs with gap 2 |
| --- | --- | --- | --- | --- | --- |
| S17 | stale_context | C2 | 2, 0, 2 | 2 | 1 of 3 |
| S18 | tool_error_ignored | C3 | 2, 1, 0 | 2 | 1 of 3 |
| S20 | arithmetic_error | C3 | 2, 1, 2 | 0 | 2 of 3 |
| S23 | arithmetic_error | C3 | 2, 2, 2 | 0 | 3 of 3 |
| S35 | stale_context | C1 | 0, 0, 2 | 0 | 1 of 3 |
| S45 | arithmetic_error | C3 | 2, 1, 2 | 0 | 2 of 3 |
| S47 | arithmetic_error | C3 | 2, 1, 2 | 0 | 2 of 3 |
| S48 | arithmetic_error | C3 | 2, 1, 2 | 0 | 2 of 3 |
| S49 | arithmetic_error | C3 | 2, 1, 2 | 0 | 2 of 3 |
