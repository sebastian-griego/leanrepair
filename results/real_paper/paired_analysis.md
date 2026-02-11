# Paired Policy Analysis

- Baseline policy: `heuristic`
- Compared policy: `research`
- Total paired items: `900`
- Discordant pairs: `595`
- `research` wins on discordant pairs: `100.0%`
- Exact paired binomial p-value (two-sided): `1.542e-179`

## Pooled Outcomes

| Outcome | Count |
|---|---:|
| both solve | 90 |
| heuristic only | 0 |
| research only | 595 |
| neither solve | 215 |

## By Corruption

| Corruption | N | Baseline Only | Compared Only | p-value |
|---|---:|---:|---:|---:|
| lowercase_type | 118 | 0 | 109 | 3.081e-33 |
| not_proposition | 194 | 0 | 99 | 3.155e-30 |
| parse_missing_colon | 176 | 0 | 57 | 1.388e-17 |
| parse_unbalanced_paren | 143 | 0 | 117 | 1.204e-35 |
| type_mismatch | 140 | 0 | 134 | 9.184e-41 |
| unknown_type_symbol | 129 | 0 | 79 | 3.309e-24 |
