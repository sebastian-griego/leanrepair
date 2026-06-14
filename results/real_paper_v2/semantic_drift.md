# LeanRepair Semantic Drift Audit

- Root: `results\real_paper_v2`
- Policies: `heuristic, research`
- Low token-recall floor: `0.20`

## Aggregate

| Policy | Records | Solved | Exact | Degenerate Solved | Nondegenerate Solved | Degenerate Given Solved | Avg Target Token Recall | Avg Binder Retention |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| heuristic | 900 | 90 | 0 | 90 | 0 | 100.0% | 14.7% | 100.0% |
| research | 900 | 756 | 251 | 504 | 252 | 66.7% | 37.9% | 95.5% |

## Degenerate Reasons

| Policy | goal_true | reflexive_equality | bare_identifier_goal | low_target_token_recall |
|---|---:|---:|---:|---:|
| heuristic | 0 | 78 | 12 | 0 |
| research | 338 | 157 | 9 | 0 |

## By Corruption

### heuristic

| Corruption | N | Solved | Exact | Degenerate | Degenerate Given Solved | Avg Token Recall |
|---|---:|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 0 | 0 | 0 | 0.0% | - |
| not_proposition | 194 | 86 | 0 | 86 | 100.0% | 14.3% |
| parse_missing_colon | 176 | 0 | 0 | 0 | 0.0% | - |
| parse_unbalanced_paren | 143 | 2 | 0 | 2 | 100.0% | 35.0% |
| type_mismatch | 140 | 2 | 0 | 2 | 100.0% | 12.5% |
| unknown_type_symbol | 129 | 0 | 0 | 0 | 0.0% | - |

### research

| Corruption | N | Solved | Exact | Degenerate | Degenerate Given Solved | Avg Token Recall |
|---|---:|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 107 | 84 | 23 | 21.5% | 78.5% |
| not_proposition | 194 | 185 | 0 | 185 | 100.0% | 7.3% |
| parse_missing_colon | 176 | 122 | 91 | 31 | 25.4% | 74.6% |
| parse_unbalanced_paren | 143 | 127 | 71 | 56 | 44.1% | 56.3% |
| type_mismatch | 140 | 136 | 0 | 136 | 100.0% | 14.9% |
| unknown_type_symbol | 129 | 79 | 5 | 73 | 92.4% | 7.9% |

## Most Severe Degenerate Solves

### heuristic

| id | corruption | reason | token recall | final goal | target goal |
|---|---|---|---:|---|---|
| real_00013 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | (a → b ∨ c) ↔ (a → b) ∨ (a → c) |
| real_00025 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | b ≤ a \|\|\| b |
| real_00027 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | UInt8.ofBitVec a < UInt8.ofBitVec b ↔ a < b |
| real_00028 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | x.toInt ≠ y.toInt ↔ x ≠ y |
| real_00032 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | 0 < numBits |
| real_00038 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | UInt32.ofFin a ≤ UInt32.ofFin b ↔ a ≤ b |
| real_00055 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | x < y ↔ x.toInt < y.toInt |
| real_00083 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | x < y ↔ x.toInt < y.toInt |
| real_00086 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | l.tail ≠ [] → l ≠ [] |
| real_00091 | not_proposition | reflexive_equality | 0.0% | Nat = Nat | ∀ {o₁ o₂ : Ordering}, (o₁.then o₂).isGE → o₁.isGE |

### research

| id | corruption | reason | token recall | final goal | target goal |
|---|---|---|---:|---|---|
| real_00012 | parse_missing_colon | goal_true | 0.0% | True | l = [] |
| real_00015 | parse_missing_colon | goal_true | 0.0% | True | (a → b) ↔ (c → d) |
| real_00027 | parse_unbalanced_paren | goal_true | 0.0% | True | False |
| real_00030 | parse_missing_colon | goal_true | 0.0% | True | Eq (f a) (g a) |
| real_00044 | parse_unbalanced_paren | goal_true | 0.0% | True | x.getLsbD i = (decide (i < w) && x.getMsbD (w - 1 - i)) |
| real_00050 | parse_missing_colon | goal_true | 0.0% | True | xs = #[] |
| real_00065 | parse_missing_colon | goal_true | 0.0% | True | { x // p x } → Exists (fun x => p x) |
| real_00071 | parse_missing_colon | goal_true | 0.0% | True | s ++ t ≠ [] |
| real_00072 | parse_missing_colon | goal_true | 0.0% | True | (a → b ∨ c) ↔ (a → b) ∨ (a → c) |
| real_00080 | parse_unbalanced_paren | goal_true | 0.0% | True | Not (LE.le n m) |
