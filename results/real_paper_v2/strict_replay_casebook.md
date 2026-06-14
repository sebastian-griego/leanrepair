# LeanRepair Strict Replay Casebook

- Records: 1800
- Focused cases: 597
- Policies: `heuristic, research`

## Primary Case Counts

| case | count |
|---|---:|
| `raw_to_strict_loss` | 586 |
| `strict_exact_accept` | 249 |
| `strict_nonexact_accept` | 11 |
| `unsolved` | 954 |

## Flag Counts

| flag | count |
|---|---:|
| `raw_to_strict_loss` | 586 |
| `strict_nonexact_accept` | 11 |

## Raw Loss Reasons

| reason | count |
|---|---:|
| `goal_true` | 338 |
| `low_target_token_recall` | 13 |
| `reflexive_equality` | 235 |

## Raw Solves Lost Under Strict Replay

| run | policy | id | corruption | raw_reason | raw_step_index | raw_final_goal | target_goal |
|---|---|---|---|---|---|---|---|
| run_20260211_002138 | heuristic | real_00048 | not_proposition | low_target_token_recall | 2 | m | n * (m - 1) = n * m - n |
| run_20260211_002407 | heuristic | real_00026 | not_proposition | low_target_token_recall | 2 | y | x % y = if 0 < y ∧ y ≤ x then (x - y) % y else x |
| run_20260211_002407 | heuristic | real_00059 | not_proposition | low_target_token_recall | 2 | b | a.toUInt32 = b.toUInt32 ↔ a % 4294967296 = b % 4294967296 |
| run_20260211_002407 | heuristic | real_00082 | not_proposition | low_target_token_recall | 2 | b | (a + b).bmod n = (a.bmod n + b.bmod n).bmod n |
| run_20260211_002407 | heuristic | real_00109 | not_proposition | low_target_token_recall | 2 | c | (a * b + c) % b = c % b |
| run_20260211_002407 | heuristic | real_00263 | not_proposition | low_target_token_recall | 2 | b | (a * b).fmod n = (a.fmod n * b.fmod n).fmod n |
| run_20260211_002639 | heuristic | real_00244 | type_mismatch | low_target_token_recall | 3 | y | y != 0 → -1 * (x % y) ≤ 0 |
| run_20260211_002138 | heuristic | real_00037 | not_proposition | reflexive_equality | 2 | Nat = Nat | ~~~a ^^^ b = ~~~(a ^^^ b) |
| run_20260211_002138 | heuristic | real_00064 | not_proposition | reflexive_equality | 2 | Nat = Nat | xs[i]? = some b ↔ ∃ h : i < xs.size, xs[i] = b |
| run_20260211_002138 | heuristic | real_00070 | not_proposition | reflexive_equality | 2 | Nat = Nat | (h : α = β) → (a : α) → cast h a ≍ a |
| run_20260211_002138 | heuristic | real_00077 | not_proposition | reflexive_equality | 2 | Nat = Nat | ∀ (x y z : Bool), (x \|\| y && z) = ((x \|\| y) && (x \|\| z)) |
| run_20260211_002138 | heuristic | real_00091 | not_proposition | reflexive_equality | 2 | Nat = Nat | ∀ {o₁ o₂ : Ordering}, (o₁.then o₂).isGE → o₁.isGE |
| run_20260211_002138 | heuristic | real_00098 | not_proposition | reflexive_equality | 2 | Nat = Nat | ∀ {x y : Bool}, (x \|\| y) = true ↔ x = true ∨ y = true |
| run_20260211_002138 | heuristic | real_00112 | not_proposition | reflexive_equality | 2 | Nat = Nat | (a::as).enum = (0, a) :: as.enumFrom 1 |
| run_20260211_002138 | heuristic | real_00120 | not_proposition | reflexive_equality | 2 | Nat = Nat | (a ^^^ b) / 2 ^ n = a / 2 ^ n ^^^ b / 2 ^ n |
| run_20260211_002138 | heuristic | real_00123 | not_proposition | reflexive_equality | 2 | Nat = Nat | x.toInt = y.toInt ↔ x = y |
| run_20260211_002138 | heuristic | real_00136 | not_proposition | reflexive_equality | 2 | Nat = Nat | ∀ {o₁ o₂ : Ordering}, (o₁.then o₂).isGT = (o₁.isGT \|\| o₁.isEq && o₂.isGT) |
| run_20260211_002138 | heuristic | real_00137 | not_proposition | reflexive_equality | 2 | Nat = Nat | x.sdiv 0#n = 0#n |
| run_20260211_002138 | heuristic | real_00162 | not_proposition | reflexive_equality | 2 | Nat = Nat | some a = l[n]? ↔ ∃ h : n < w, l[n] = a |
| run_20260211_002138 | heuristic | real_00174 | not_proposition | reflexive_equality | 2 | Nat = Nat | a ≤ b ↔ a.toBitVec.sle b.toBitVec |
| run_20260211_002138 | heuristic | real_00177 | not_proposition | reflexive_equality | 2 | Nat = Nat | xs.insertIdx n x = xs.push x |
| run_20260211_002138 | heuristic | real_00185 | not_proposition | reflexive_equality | 2 | Nat = Nat | {x y : Int8} → x.toBitVec = y.toBitVec → x = y |
| run_20260211_002138 | heuristic | real_00209 | not_proposition | reflexive_equality | 2 | Nat = Nat | ∀ {a b c : Int}, a ∣ b → b ∣ c → b.fdiv a ∣ c.fdiv a |
| run_20260211_002138 | heuristic | real_00219 | not_proposition | reflexive_equality | 2 | Nat = Nat | a ≤ b ↔ a.toFin ≤ b.toFin |
| run_20260211_002138 | heuristic | real_00222 | not_proposition | reflexive_equality | 2 | Nat = Nat | Or (Eq numBits 32) (Eq numBits 64) |

## Strict Nonexact Accepts

| run | policy | id | corruption | strict_step_index | strict_final_header | target_header |
|---|---|---|---|---|---|---|
| run_20260211_002138 | heuristic | real_00255 | not_proposition | 2 | theorem bench_real_00255 (a b : Int) (b : Prop): b | theorem bench_real_00255 (a b : Int) : (¬a ≤ b) = (b + 1 ≤ a) |
| run_20260211_002407 | heuristic | real_00296 | not_proposition | 2 | theorem bench_real_00296 (x y : Int) (y : Prop): y | theorem bench_real_00296 (x y : Int) : (x - y) % y = x % y |
| run_20260211_002639 | heuristic | real_00111 | not_proposition | 2 | theorem bench_real_00111 (n m : Nat) (h : 0 < m) (m : Prop): m | theorem bench_real_00111 (n m : Nat) (h : 0 < m) : 1 ≤ m ^ n |
| run_20260211_002639 | heuristic | real_00066 | parse_unbalanced_paren | 4 | theorem bench_real_00066 {n d : Nat} (d : Prop): d | theorem bench_real_00066 {n d : Nat} : d * (n / d) = n ↔ d ∣ n |
| run_20260211_002639 | heuristic | real_00288 | parse_unbalanced_paren | 3 | theorem bench_real_00288 [Decidable a] : a | theorem bench_real_00288 [Decidable a] : a ∨ b ↔ (¬a → b) |
| run_20260211_002138 | research | real_00255 | not_proposition | 2 | theorem bench_real_00255 (a b : Int) (b : Prop): b | theorem bench_real_00255 (a b : Int) : (¬a ≤ b) = (b + 1 ≤ a) |
| run_20260211_002407 | research | real_00296 | not_proposition | 2 | theorem bench_real_00296 (x y : Int) (y : Prop): y | theorem bench_real_00296 (x y : Int) : (x - y) % y = x % y |
| run_20260211_002639 | research | real_00111 | not_proposition | 2 | theorem bench_real_00111 (n m : Nat) (h : 0 < m) (m : Prop): m | theorem bench_real_00111 (n m : Nat) (h : 0 < m) : 1 ≤ m ^ n |
| run_20260211_002138 | research | real_00139 | parse_missing_colon | 2 | theorem bench_real_00139 (a : α) : a = a ↔ True | theorem bench_real_00139 (a : α) : a = a ↔ True |
| run_20260211_002407 | research | real_00230 | parse_missing_colon | 2 | theorem bench_real_00230 : ∀ (x y z : Bool), (x && (y \|\| z)) = (x && y \|\| x && z) | theorem bench_real_00230 : ∀ (x y z : Bool), (x && (y \|\| z)) = (x && y \|\| x && z) |
| run_20260211_002407 | research | real_00075 | unknown_type_symbol | 2 | theorem bench_real_00075 {a b : Nat} (hab : b ≤ a) : Int.ofNat (a - b) = UInt8.ofNat a... | theorem bench_real_00075 {a b : Nat} (hab : b ≤ a) : UInt8.ofNat (a - b) = UInt8.ofNat... |

## Recoveries After Degenerate Raw Candidates

No cases.

## Changed Accepted Outputs

No cases.
