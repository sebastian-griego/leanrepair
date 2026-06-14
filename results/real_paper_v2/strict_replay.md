# LeanRepair Strict Replay Audit

- Root: `results\real_paper_v2`
- Policies: `heuristic, research`
- Low token-recall floor: `0.20`

## Aggregate

| Policy | Records | Raw Solved | Strict Solved | Raw Exact | Strict Exact | Strict Nonexact | Exact Given Strict | Raw Degenerate | Lost Under Strict | Strict Retention | Recovered Later |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| heuristic | 900 | 90 | 0 | 0 | 0 | 0 | 0.0% | 90 | 90 | 0.0% | 0 |
| research | 900 | 756 | 252 | 251 | 251 | 1 | 99.6% | 504 | 504 | 33.3% | 0 |

## Raw Degenerate Reasons

| Policy | goal_true | reflexive_equality | bare_identifier_goal | low_target_token_recall |
|---|---:|---:|---:|---:|
| heuristic | 0 | 78 | 12 | 0 |
| research | 338 | 157 | 9 | 0 |

## By Corruption

### heuristic

| Corruption | N | Raw Solved | Strict Solved | Strict Exact | Strict Nonexact | Exact Given Strict | Raw Degenerate | Lost | Retention |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 0 | 0 | 0 | 0 | 0.0% | 0 | 0 | 0.0% |
| not_proposition | 194 | 86 | 0 | 0 | 0 | 0.0% | 86 | 86 | 0.0% |
| parse_missing_colon | 176 | 0 | 0 | 0 | 0 | 0.0% | 0 | 0 | 0.0% |
| parse_unbalanced_paren | 143 | 2 | 0 | 0 | 0 | 0.0% | 2 | 2 | 0.0% |
| type_mismatch | 140 | 2 | 0 | 0 | 0 | 0.0% | 2 | 2 | 0.0% |
| unknown_type_symbol | 129 | 0 | 0 | 0 | 0 | 0.0% | 0 | 0 | 0.0% |

### research

| Corruption | N | Raw Solved | Strict Solved | Strict Exact | Strict Nonexact | Exact Given Strict | Raw Degenerate | Lost | Retention |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 107 | 84 | 84 | 0 | 100.0% | 23 | 23 | 78.5% |
| not_proposition | 194 | 185 | 0 | 0 | 0 | 0.0% | 185 | 185 | 0.0% |
| parse_missing_colon | 176 | 122 | 91 | 91 | 0 | 100.0% | 31 | 31 | 74.6% |
| parse_unbalanced_paren | 143 | 127 | 71 | 71 | 0 | 100.0% | 56 | 56 | 55.9% |
| type_mismatch | 140 | 136 | 0 | 0 | 0 | 0.0% | 136 | 136 | 0.0% |
| unknown_type_symbol | 129 | 79 | 6 | 5 | 1 | 83.3% | 73 | 73 | 7.6% |

## Raw Solves Rejected By Strict Replay

### heuristic

| id | corruption | reason | raw step | raw final goal | target goal |
|---|---|---|---:|---|---|
| real_00026 | not_proposition | bare_identifier_goal | 2 | y | x % y = if 0 < y ∧ y ≤ x then (x - y) % y else x |
| real_00048 | not_proposition | bare_identifier_goal | 2 | m | n * (m - 1) = n * m - n |
| real_00059 | not_proposition | bare_identifier_goal | 2 | b | a.toUInt32 = b.toUInt32 ↔ a % 4294967296 = b % 4294967296 |
| real_00082 | not_proposition | bare_identifier_goal | 2 | b | (a + b).bmod n = (a.bmod n + b.bmod n).bmod n |
| real_00109 | not_proposition | bare_identifier_goal | 2 | c | (a * b + c) % b = c % b |
| real_00111 | not_proposition | bare_identifier_goal | 2 | m | 1 ≤ m ^ n |
| real_00255 | not_proposition | bare_identifier_goal | 2 | b | (¬a ≤ b) = (b + 1 ≤ a) |
| real_00263 | not_proposition | bare_identifier_goal | 2 | b | (a * b).fmod n = (a.fmod n * b.fmod n).fmod n |
| real_00296 | not_proposition | bare_identifier_goal | 2 | y | (x - y) % y = x % y |
| real_00066 | parse_unbalanced_paren | bare_identifier_goal | 4 | d | d * (n / d) = n ↔ d ∣ n |

### research

| id | corruption | reason | raw step | raw final goal | target goal |
|---|---|---|---:|---|---|
| real_00026 | not_proposition | bare_identifier_goal | 2 | y | x % y = if 0 < y ∧ y ≤ x then (x - y) % y else x |
| real_00048 | not_proposition | bare_identifier_goal | 2 | m | n * (m - 1) = n * m - n |
| real_00059 | not_proposition | bare_identifier_goal | 2 | b | a.toUInt32 = b.toUInt32 ↔ a % 4294967296 = b % 4294967296 |
| real_00082 | not_proposition | bare_identifier_goal | 2 | b | (a + b).bmod n = (a.bmod n + b.bmod n).bmod n |
| real_00109 | not_proposition | bare_identifier_goal | 2 | c | (a * b + c) % b = c % b |
| real_00111 | not_proposition | bare_identifier_goal | 2 | m | 1 ≤ m ^ n |
| real_00255 | not_proposition | bare_identifier_goal | 2 | b | (¬a ≤ b) = (b + 1 ≤ a) |
| real_00263 | not_proposition | bare_identifier_goal | 2 | b | (a * b).fmod n = (a.fmod n * b.fmod n).fmod n |
| real_00296 | not_proposition | bare_identifier_goal | 2 | y | (x - y) % y = x % y |
| real_00000 | lowercase_type | goal_true | 2 | True | x.toInt = y.toInt ↔ x = y |

## Strict Nonexact Accepts

### heuristic

Every strict accepted candidate is exact.

### research

| id | corruption | strict step | strict final header | target header |
|---|---|---:|---|---|
| real_00075 | unknown_type_symbol | 2 | theorem bench_real_00075 {a b : Nat} (hab : b ≤ a) : Int.ofNat (a - b) = UInt8.ofNat a - UInt8.ofNat b | theorem bench_real_00075 {a b : Nat} (hab : b ≤ a) : UInt8.ofNat (a - b) = UInt8.ofNat a - UInt8.ofNat b |

## Later Nondegenerate Recoveries

### heuristic

No trace contains a later nondegenerate accepted candidate after a degenerate one.

### research

No trace contains a later nondegenerate accepted candidate after a degenerate one.
