# LeanRepair Real Paper v2 Snapshot

- Root: `results/real_paper_v2`
- Runs: `3`
- Records per policy: `heuristic` 900, `research` 900

## Raw Aggregate Outcomes

| Policy | Records | Solved | Solve rate | Exact | Exact rate | Mean solve | Mean exact |
|---|---:|---:|---:|---:|---:|---:|---:|
| `heuristic` | 900 | 90 | 10.0% [8.2, 12.1] | 0 | 0.0% [0.0, 0.4] | 10.0% +/- 1.2% | 0.0% +/- 0.0% |
| `research` | 900 | 756 | 84.0% [81.5, 86.2] | 249 | 27.7% [24.8, 30.7] | 84.0% +/- 1.1% | 27.7% +/- 3.1% |

## Quality-Adjusted Outcomes

| Policy | Records | Raw solved | Exact | Nondegenerate solved | Degenerate solved | Nondegenerate rate | Degenerate given solved |
|---|---:|---:|---:|---:|---:|---:|---:|
| `heuristic` | 900 | 90 | 0 | 0 | 90 | 0.0% [0.0, 0.4] | 100.0% |
| `research` | 900 | 756 | 251 | 252 | 504 | 28.0% [25.2, 31.0] | 66.7% |

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
- `quality`: `results/real_paper_v2/quality_summary.json`
- `semantic_drift`: `results/real_paper_v2/semantic_drift.json`
- `strict_replay`: `results/real_paper_v2/strict_replay.json`
- `strict_casebook`: `results/real_paper_v2/strict_replay_casebook.json`
- `strict_paired`: `results/real_paper_v2/strict_replay_paired.json`
