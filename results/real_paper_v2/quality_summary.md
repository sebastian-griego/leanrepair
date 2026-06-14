# LeanRepair Quality-Adjusted Summary

- Root: `results\real_paper_v2`
- Runs: `3`
- Token-recall floor: `0.20`

## Pooled Metrics

| Policy | Records | Solved | Exact | Nondegenerate Solved | Degenerate Solved | Pooled Solve | Pooled Exact | Pooled Nondegenerate | Degenerate Given Solved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| heuristic | 900 | 90 | 0 | 5 | 85 | 10.0% [8.2, 12.1] | 0.0% [0.0, 0.4] | 0.6% [0.2, 1.3] | 94.4% |
| research | 900 | 756 | 249 | 255 | 501 | 84.0% [81.5, 86.2] | 27.7% [24.8, 30.7] | 28.3% [25.5, 31.4] | 66.3% |

## Mean Across Runs

| Policy | Solve Rate | Exact Rate | Nondegenerate Rate | Degenerate Rate |
|---|---:|---:|---:|---:|
| heuristic | 10.0% +/- 1.5% | 0.0% +/- 0.0% | 0.6% +/- 0.4% | 9.4% +/- 1.2% |
| research | 84.0% +/- 1.3% | 27.7% +/- 3.8% | 28.3% +/- 3.9% | 55.7% +/- 3.8% |

## Pooled By Corruption

### heuristic

| Corruption | N | Solved | Exact | Nondegenerate | Degenerate | Nondegenerate Rate |
|---|---:|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 0 | 0 | 0 | 0 | 0.0% |
| not_proposition | 194 | 86 | 0 | 3 | 83 | 1.5% |
| parse_missing_colon | 176 | 0 | 0 | 0 | 0 | 0.0% |
| parse_unbalanced_paren | 143 | 2 | 0 | 2 | 0 | 1.4% |
| type_mismatch | 140 | 2 | 0 | 0 | 2 | 0.0% |
| unknown_type_symbol | 129 | 0 | 0 | 0 | 0 | 0.0% |

### research

| Corruption | N | Solved | Exact | Nondegenerate | Degenerate | Nondegenerate Rate |
|---|---:|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 107 | 84 | 84 | 23 | 71.2% |
| not_proposition | 194 | 185 | 0 | 3 | 182 | 1.5% |
| parse_missing_colon | 176 | 122 | 89 | 91 | 31 | 51.7% |
| parse_unbalanced_paren | 143 | 127 | 71 | 71 | 56 | 49.7% |
| type_mismatch | 140 | 136 | 0 | 0 | 136 | 0.0% |
| unknown_type_symbol | 129 | 79 | 5 | 6 | 73 | 4.7% |
