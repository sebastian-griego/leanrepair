# LeanRepair Real-Data Results (AI-Style)

Dataset:
- 3 seeds x 300 items = 900 total
- Real theorem/lemma headers mined from Lean source
- Same fixed benchmark files for both policies (`data/real_benchmark_seed7.jsonl`, `data/real_benchmark_seed17.jsonl`, `data/real_benchmark_seed27.jsonl`)

## Main Table (mean ± std over 3 seeds)

| Policy | Solve Rate | Exact Rate | Avg Steps | Avg Time (ms/item) |
|---|---:|---:|---:|---:|
| heuristic | 10.0% ± 1.2% | 0.0% ± 0.0% | 1.32 ± 0.03 | 255.9 ± 6.3 |
| research | 84.0% ± 1.1% | 27.7% ± 3.1% | 2.55 ± 0.01 | 494.4 ± 2.2 |

## Pass@k (pooled over 900 items)

| Policy | pass@2 | pass@3 | pass@4 | pass@6 |
|---|---:|---:|---:|---:|
| heuristic | 9.56% | 9.78% | 10.00% | 10.00% |
| research | 62.67% | 73.56% | 83.00% | 84.00% |

## Head-to-Head (paired over same 900 items)

- both solved: 90
- heuristic-only: 0
- research-only: 666
- neither solved: 144

## Per-Corruption Solve Rate (pooled)

| Corruption | heuristic | research |
|---|---:|---:|
| lowercase_type | 0.0% | 90.7% |
| not_proposition | 44.3% | 95.4% |
| parse_missing_colon | 0.0% | 69.3% |
| parse_unbalanced_paren | 1.4% | 88.8% |
| type_mismatch | 1.4% | 97.1% |
| unknown_type_symbol | 0.0% | 61.2% |
