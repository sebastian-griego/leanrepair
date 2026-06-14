# LeanRepair Real Paper v2 Snapshot

- Root: `results/real_paper_v2`
- Runs: `3`
- Records per policy: `heuristic` 900, `research` 900

## Raw Aggregate Outcomes

| Policy | Records | Solved | Solve rate | Exact | Exact rate | Mean solve | Mean exact |
|---|---:|---:|---:|---:|---:|---:|---:|
| `heuristic` | 900 | 90 | 10.0% [8.2, 12.1] | 0 | 0.0% [0.0, 0.4] | 10.0% +/- 1.2% | 0.0% +/- 0.0% |
| `research` | 900 | 756 | 84.0% [81.5, 86.2] | 249 | 27.7% [24.8, 30.7] | 84.0% +/- 1.1% | 27.7% +/- 3.1% |

## Repair Budget Curve

| Policy | Final budget | Final solved | Solve rate | Exact | Exact rate | Avg checks | Marginal solves |
|---|---:|---:|---:|---:|---:|---:|---|
| `heuristic` | 4 | 90 | 10.0% | 0 | 0.0% | 1.32 | `1` 0, `2` 86, `3` 2, `4` 2 |
| `research` | 6 | 756 | 84.0% | 249 | 27.7% | 2.55 | `1` 0, `2` 564, `3` 98, `4` 85, `5` 4, `6` 5 |

## Exactness Gap

| Policy | Records | Solved | Exact | Solved not exact | Solve-exact gap | Exact given solved | Drift given solved | Avg header similarity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `heuristic` | 900 | 90 | 0 | 90 | +10.0 pp | 0.0% | 100.0% | 61.3% |
| `research` | 900 | 756 | 249 | 507 | +56.3 pp | 32.9% | 67.1% | 76.0% |

## Quality-Adjusted Outcomes

| Policy | Records | Raw solved | Exact | Nondegenerate solved | Degenerate solved | Nondegenerate rate | Degenerate given solved |
|---|---:|---:|---:|---:|---:|---:|---:|
| `heuristic` | 900 | 90 | 0 | 0 | 90 | 0.0% [0.0, 0.4] | 100.0% |
| `research` | 900 | 756 | 251 | 252 | 504 | 28.0% [25.2, 31.0] | 66.7% |

## Trace Taxonomy

| Policy | Records | Lean-OK rate | Exact rate | Avg steps | Median solve step | Top terminal failure | Timeouts |
|---|---:|---:|---:|---:|---:|---|---:|
| `heuristic` | 900 | 10.0% | 0.0% | 1.32 | 2.0 | `parse_error` 315 | 0 |
| `research` | 900 | 84.0% | 27.7% | 2.55 | 2.0 | `parse_error` 59 | 0 |

## Corruption Highlights

| Policy | Corruption | Records | Final solve | Final exact | Exact given solved | Top terminal failure |
|---|---|---:|---:|---:|---:|---|
| `heuristic` | `lowercase_type` | 118 | 0.0% | 0.0% | 0.0% | `failed_typeclass` 65 |
| `heuristic` | `not_proposition` | 194 | 44.3% | 0.0% | 0.0% | `type_mismatch` 101 |
| `heuristic` | `parse_missing_colon` | 176 | 0.0% | 0.0% | 0.0% | `parse_error` 176 |
| `heuristic` | `parse_unbalanced_paren` | 143 | 1.4% | 0.0% | 0.0% | `parse_error` 129 |
| `heuristic` | `type_mismatch` | 140 | 1.4% | 0.0% | 0.0% | `type_mismatch` 112 |
| `heuristic` | `unknown_type_symbol` | 129 | 0.0% | 0.0% | 0.0% | `failed_typeclass` 62 |
| `research` | `lowercase_type` | 118 | 90.7% | 71.2% | 78.5% | `other` 5 |
| `research` | `not_proposition` | 194 | 95.4% | 0.0% | 0.0% | `other` 8 |
| `research` | `parse_missing_colon` | 176 | 69.3% | 50.6% | 73.0% | `parse_error` 46 |
| `research` | `parse_unbalanced_paren` | 143 | 88.8% | 49.7% | 55.9% | `parse_error` 13 |
| `research` | `type_mismatch` | 140 | 97.1% | 0.0% | 0.0% | `other` 3 |
| `research` | `unknown_type_symbol` | 129 | 61.2% | 3.9% | 6.3% | `failed_typeclass` 26 |

## Strict Replay

| Policy | Raw solved | Strict solved | Strict exact | Strict nonexact | Raw-to-strict loss | Strict retention | Strict exact given strict |
|---|---:|---:|---:|---:|---:|---:|---:|
| `heuristic` | 90 | 0 | 0 | 0 | 90 | 0.0% | 0.0% |
| `research` | 756 | 252 | 251 | 1 | 504 | 33.3% | 99.6% |

## Strict Paired Comparison

- Baseline policy: `heuristic`
- Compared policy: `research`
- Paired records: `900`

| Metric | Baseline successes | Compared successes | Compared-only | Baseline-only | Lift | Sign-test p |
|---|---:|---:|---:|---:|---:|---:|
| `raw_ok` | 90 | 756 | 666 | 0 | +74.0 pp | 6.532e-201 |
| `strict_ok` | 0 | 252 | 252 | 0 | +28.0 pp | 2.764e-76 |
| `strict_exact` | 0 | 251 | 251 | 0 | +27.9 pp | 5.527e-76 |

## Degenerate Losses

| Source | Total | Breakdown |
|---|---:|---|
| strict replay casebook raw-to-strict loss | 594 | `bare_identifier_goal` 21, `goal_true` 338, `reflexive_equality` 235 |
| compared-policy raw wins lost under strict replay | 414 | `goal_true` 334, `reflexive_equality` 80 |

## Sources

- `aggregate`: `results/real_paper_v2/aggregate_summary.json`
- `budget_curve`: `results/real_paper_v2/budget_curve.json`
- `exactness_gap`: `results/real_paper_v2/exactness_gap.json`
- `quality`: `results/real_paper_v2/quality_summary.json`
- `semantic_drift`: `results/real_paper_v2/semantic_drift.json`
- `strict_replay`: `results/real_paper_v2/strict_replay.json`
- `strict_casebook`: `results/real_paper_v2/strict_replay_casebook.json`
- `strict_paired`: `results/real_paper_v2/strict_replay_paired.json`
- `trace_taxonomy`: `results/real_paper_v2/trace_taxonomy.json`
