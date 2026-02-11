# Paired Policy Analysis

- Baseline policy: `heuristic`
- Compared policy: `research`
- Total paired items: `900`
- Discordant pairs: `666`
- `research` wins on discordant pairs: `100.0%`
- Exact paired binomial p-value (two-sided): `6.532e-201`

## Pooled Outcomes

| Outcome | Count |
|---|---:|
| both solve | 90 |
| heuristic only | 0 |
| research only | 666 |
| neither solve | 144 |

## By Corruption

| Corruption | N | Baseline Only | Compared Only | p-value |
|---|---:|---:|---:|---:|
| lowercase_type | 118 | 0 | 107 | 1.233e-32 |
| not_proposition | 194 | 0 | 99 | 3.155e-30 |
| parse_missing_colon | 176 | 0 | 122 | 3.762e-37 |
| parse_unbalanced_paren | 143 | 0 | 125 | 4.702e-38 |
| type_mismatch | 140 | 0 | 134 | 9.184e-41 |
| unknown_type_symbol | 129 | 0 | 79 | 3.309e-24 |
