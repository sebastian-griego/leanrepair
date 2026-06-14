# LeanRepair Repair-Budget Curve

- Root: `results\real_paper_v2`
- Policies: `heuristic, research`

## Aggregate Budget Curve

| Policy | Budget | Solve Rate | Exact Rate | Solved | Exact | Avg Checks Used | Marginal Solves |
|---|---:|---:|---:|---:|---:|---:|---:|
| heuristic | 1 | 0.0% | 0.0% | 0 | 0 | 1.00 | 0 |
| heuristic | 2 | 9.6% | 0.0% | 86 | 0 | 1.29 | 86 |
| heuristic | 3 | 9.8% | 0.0% | 88 | 0 | 1.32 | 2 |
| heuristic | 4 | 10.0% | 0.0% | 90 | 0 | 1.32 | 2 |
| research | 1 | 0.0% | 0.0% | 0 | 0 | 1.00 | 0 |
| research | 2 | 62.7% | 18.9% | 564 | 170 | 2.00 | 564 |
| research | 3 | 73.6% | 19.8% | 662 | 178 | 2.31 | 98 |
| research | 4 | 83.0% | 27.7% | 747 | 249 | 2.48 | 85 |
| research | 5 | 83.4% | 27.7% | 751 | 249 | 2.52 | 4 |
| research | 6 | 84.0% | 27.7% | 756 | 249 | 2.55 | 5 |

## Final By Corruption

### heuristic

| Corruption | Final Solve Rate | Final Exact Rate | Final Solved | Final Exact |
|---|---:|---:|---:|---:|
| lowercase_type | 0.0% | 0.0% | 0 | 0 |
| not_proposition | 44.3% | 0.0% | 86 | 0 |
| parse_missing_colon | 0.0% | 0.0% | 0 | 0 |
| parse_unbalanced_paren | 1.4% | 0.0% | 2 | 0 |
| type_mismatch | 1.4% | 0.0% | 2 | 0 |
| unknown_type_symbol | 0.0% | 0.0% | 0 | 0 |

### research

| Corruption | Final Solve Rate | Final Exact Rate | Final Solved | Final Exact |
|---|---:|---:|---:|---:|
| lowercase_type | 90.7% | 71.2% | 107 | 84 |
| not_proposition | 95.4% | 0.0% | 185 | 0 |
| parse_missing_colon | 69.3% | 50.6% | 122 | 89 |
| parse_unbalanced_paren | 88.8% | 49.7% | 127 | 71 |
| type_mismatch | 97.1% | 0.0% | 136 | 0 |
| unknown_type_symbol | 61.2% | 3.9% | 79 | 5 |

