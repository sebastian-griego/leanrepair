# LeanRepair Strict Replay Audit

- Root: `results\real_paper_v2`
- Policies: `heuristic, research`
- Low token-recall floor: `0.20`

## Aggregate

| Policy | Records | Raw Solved | Strict Solved | Raw Exact | Strict Exact | Raw Degenerate | Lost Under Strict | Strict Retention | Recovered Later |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| heuristic | 900 | 90 | 5 | 0 | 0 | 85 | 85 | 5.6% | 0 |
| research | 900 | 756 | 255 | 249 | 249 | 501 | 501 | 33.7% | 0 |

## Raw Degenerate Reasons

| Policy | goal_true | reflexive_equality | low_target_token_recall |
|---|---:|---:|---:|
| heuristic | 0 | 78 | 7 |
| research | 338 | 157 | 6 |

## By Corruption

### heuristic

| Corruption | N | Raw Solved | Strict Solved | Raw Degenerate | Lost | Retention |
|---|---:|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 0 | 0 | 0 | 0 | 0.0% |
| not_proposition | 194 | 86 | 3 | 83 | 83 | 3.5% |
| parse_missing_colon | 176 | 0 | 0 | 0 | 0 | 0.0% |
| parse_unbalanced_paren | 143 | 2 | 2 | 0 | 0 | 100.0% |
| type_mismatch | 140 | 2 | 0 | 2 | 2 | 0.0% |
| unknown_type_symbol | 129 | 0 | 0 | 0 | 0 | 0.0% |

### research

| Corruption | N | Raw Solved | Strict Solved | Raw Degenerate | Lost | Retention |
|---|---:|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 107 | 84 | 23 | 23 | 78.5% |
| not_proposition | 194 | 185 | 3 | 182 | 182 | 1.6% |
| parse_missing_colon | 176 | 122 | 91 | 31 | 31 | 74.6% |
| parse_unbalanced_paren | 143 | 127 | 71 | 56 | 56 | 55.9% |
| type_mismatch | 140 | 136 | 0 | 136 | 136 | 0.0% |
| unknown_type_symbol | 129 | 79 | 6 | 73 | 73 | 7.6% |

## Raw Solves Rejected By Strict Replay

### heuristic

| id | corruption | reason | raw step | raw final goal | target goal |
|---|---|---|---:|---|---|
| real_00026 | not_proposition | low_target_token_recall | 2 | y | x % y = if 0 < y ∧ y ≤ x then (x - y) % y else x |
| real_00048 | not_proposition | low_target_token_recall | 2 | m | n * (m - 1) = n * m - n |
| real_00059 | not_proposition | low_target_token_recall | 2 | b | a.toUInt32 = b.toUInt32 ↔ a % 4294967296 = b % 4294967296 |
| real_00082 | not_proposition | low_target_token_recall | 2 | b | (a + b).bmod n = (a.bmod n + b.bmod n).bmod n |
| real_00109 | not_proposition | low_target_token_recall | 2 | c | (a * b + c) % b = c % b |
| real_00263 | not_proposition | low_target_token_recall | 2 | b | (a * b).fmod n = (a.fmod n * b.fmod n).fmod n |
| real_00244 | type_mismatch | low_target_token_recall | 3 | y | y != 0 → -1 * (x % y) ≤ 0 |
| real_00002 | not_proposition | reflexive_equality | 2 | Nat = Nat | max a (b + a) = b + a |
| real_00008 | not_proposition | reflexive_equality | 2 | Nat = Nat | (-1 : UInt32) = 4294967295 |
| real_00010 | not_proposition | reflexive_equality | 2 | Nat = Nat | ∀ (x y z : Bool), (x && (y ^^ z)) = ((x && y) ^^ (x && z)) |

### research

| id | corruption | reason | raw step | raw final goal | target goal |
|---|---|---|---:|---|---|
| real_00000 | lowercase_type | goal_true | 2 | True | x.toInt = y.toInt ↔ x = y |
| real_00016 | lowercase_type | goal_true | 2 | True | x.toInt.toNat = x.toNat |
| real_00036 | lowercase_type | goal_true | 2 | True | a < b ↔ a.toFin < b.toFin |
| real_00041 | lowercase_type | goal_true | 2 | True | a.toInt64 ≠ Int64.minValue |
| real_00043 | lowercase_type | goal_true | 2 | True | a.fmod b + (a.fdiv b) * b = a |
| real_00054 | lowercase_type | goal_true | 2 | True | (a ^^^ b) >>> c = (a >>> c) ^^^ (b >>> c) |
| real_00087 | lowercase_type | goal_true | 2 | True | (a &&& b) >>> c = (a >>> c) &&& (b >>> c) |
| real_00107 | lowercase_type | goal_true | 2 | True | (a ^^^ b) <<< c = (a <<< c) ^^^ (b <<< c) |
| real_00111 | lowercase_type | goal_true | 2 | True | x.toInt = y.toInt → x = y |
| real_00116 | lowercase_type | goal_true | 2 | True | c.toNat ≤ 1 |

## Later Nondegenerate Recoveries

### heuristic

No trace contains a later nondegenerate accepted candidate after a degenerate one.

### research

No trace contains a later nondegenerate accepted candidate after a degenerate one.
