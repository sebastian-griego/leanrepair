# LeanRepair Strict Replay Paired Analysis

- Baseline policy: `heuristic`
- Compared policy: `research`
- Paired records: `900`
- Unpaired records: `0` heuristic-only, `0` research-only
- Raw solve lift: `+74.0 pp` (research only `666`, heuristic only `0`)
- Strict solve lift: `+28.0 pp` (research only `252`, heuristic only `0`)
- Strict exact lift: `+27.9 pp` (research only `251`, heuristic only `0`)
- Strict solve sign-test p-value: `2.764e-76`
- Strict exact sign-test p-value: `5.527e-76`
- Compared raw wins lost under strict replay: `414`

## Metric Table

| Metric | Both | Baseline only | Compared only | Neither | Baseline rate | Compared rate | Lift | p-value |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `raw_ok` | 90 | 0 | 666 | 144 | 10.0% | 84.0% | +74.0 pp | 6.532e-201 |
| `strict_ok` | 0 | 0 | 252 | 648 | 0.0% | 28.0% | +28.0 pp | 2.764e-76 |
| `strict_exact` | 0 | 0 | 251 | 649 | 0.0% | 27.9% | +27.9 pp | 5.527e-76 |

## Policy Strictness

| Policy | Raw solved | Strict solved | Strict exact | Raw degenerate | Lost under strict | Strict retention |
|---|---:|---:|---:|---:|---:|---:|
| `heuristic` | 90 | 0 | 0 | 90 | 90 | 0.0% |
| `research` | 756 | 252 | 251 | 504 | 504 | 33.3% |

## By Corruption

| Corruption | N | Strict baseline only | Strict compared only | Strict lift | Strict exact lift | Strict p-value |
|---|---:|---:|---:|---:|---:|---:|
| `lowercase_type` | 118 | 0 | 84 | +71.2 pp | +71.2 pp | 1.034e-25 |
| `not_proposition` | 194 | 0 | 0 | +0.0 pp | +0.0 pp | 1.000e+00 |
| `parse_missing_colon` | 176 | 0 | 91 | +51.7 pp | +51.7 pp | 8.078e-28 |
| `parse_unbalanced_paren` | 143 | 0 | 71 | +49.7 pp | +49.7 pp | 8.470e-22 |
| `type_mismatch` | 140 | 0 | 0 | +0.0 pp | +0.0 pp | 1.000e+00 |
| `unknown_type_symbol` | 129 | 0 | 6 | +4.7 pp | +3.9 pp | 3.125e-02 |

## Raw Wins Lost By Strict Replay Breakdown

Raw wins lost by strict replay are cases where the compared policy solved under raw Lean-ok, the baseline did not, and strict replay rejected the compared output.

- Total lost compared-policy raw wins: `414`

| Rejection reason | Count | Share |
|---|---:|---:|
| `goal_true` | 334 | 80.7% |
| `reflexive_equality` | 80 | 19.3% |

| Corruption | Count | Share |
|---|---:|---:|
| `type_mismatch` | 134 | 32.4% |
| `not_proposition` | 99 | 23.9% |
| `unknown_type_symbol` | 73 | 17.6% |
| `parse_unbalanced_paren` | 54 | 13.0% |
| `parse_missing_colon` | 31 | 7.5% |
| `lowercase_type` | 23 | 5.6% |

| Rejection reason | Corruption | Count | Share |
|---|---|---:|---:|
| `goal_true` | `not_proposition` | 99 | 23.9% |
| `reflexive_equality` | `type_mismatch` | 80 | 19.3% |
| `goal_true` | `unknown_type_symbol` | 73 | 17.6% |
| `goal_true` | `parse_unbalanced_paren` | 54 | 13.0% |
| `goal_true` | `type_mismatch` | 54 | 13.0% |
| `goal_true` | `parse_missing_colon` | 31 | 7.5% |
| `goal_true` | `lowercase_type` | 23 | 5.6% |

## research Strict Wins

| run | id | corruption | baseline raw/strict/exact | compared raw/strict/exact | compared reason | compared strict header |
|---|---|---|---:|---:|---|---|
| run_20260211_002138 | real_00016 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00016 {a b c : Nat} (h : a + b < c) : a < c - b |
| run_20260211_002138 | real_00036 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00036 {l : List α} {p q : α → Bool} (h : ∀ x ∈ l, p x → q x) : l.fin... |
| run_20260211_002138 | real_00040 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00040 (a b : Nat) : (NatCast.natCast (a + b : Nat) : Int) = (NatCast... |
| run_20260211_002138 | real_00058 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00058 {m n : Nat} (H : n % m = 0) : m ∣ n |
| run_20260211_002138 | real_00073 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00073 {a : Int} (b : Int) (Ha : 0 ≤ a) : a.tdiv b ≤ a |
| run_20260211_002138 | real_00097 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00097 {p : Fin 1 → Prop} : (∀ i, p i) ↔ p 0 |
| run_20260211_002138 | real_00105 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00105 {z : Int} (hz : z ≠ 0) : z.sign.natAbs = 1 |
| run_20260211_002138 | real_00134 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00134 {a b : Int} (hab : b ∣ a) : (a / b).natAbs = a.natAbs / b.natAbs |
| run_20260211_002138 | real_00138 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00138 (a : Int16) (ha : a ≠ -1) : a.toInt32 ≠ -1 |
| run_20260211_002138 | real_00141 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00141 : ∀ {b : Bool}, (b = false → b = true) ↔ (b = true) |
| run_20260211_002138 | real_00146 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00146 {a b : Prop} (h : b = True) : (a = b) = a |
| run_20260211_002138 | real_00148 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00148 (m k : Nat) : m % k = m - k * (m / k) |
| run_20260211_002138 | real_00151 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00151 {n m : Nat} (h : n ∣ m) : m / n ∣ m |
| run_20260211_002138 | real_00153 | lowercase_type | no/no/no | yes/yes/yes | - | theorem getElem!_of_getElem? [Inhabited α] : ∀ {l : List α} {i : Nat}, l[i]? = some a →... |
| run_20260211_002138 | real_00159 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00159 (b : Prop) : ¬a → ¬(a ∧ b) |
| run_20260211_002138 | real_00173 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00173 (a : Int8) : -a = -1 * a |
| run_20260211_002138 | real_00187 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00187 {p q : Prop} (hp : p) (hq : q) : HEq hp hq |
| run_20260211_002138 | real_00190 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00190 {c : Prop} {h : Decidable c} (hc : c) {α : Sort u} {t : c → α}... |
| run_20260211_002138 | real_00212 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00212 {m n : Nat} (H : m ∣ n) : n % m = 0 |
| run_20260211_002138 | real_00265 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00265 {n : Int} : -n < n ↔ 0 < n |
| run_20260211_002138 | real_00269 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00269 {a b : Int} {hab₁ hab₂} : Int8.ofIntLE (a * b) hab₁ hab₂ = Int... |
| run_20260211_002138 | real_00277 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00277 : ∀ {x y z : Bool}, (x ^^ y) = (x ^^ z) ↔ y = z |
| run_20260211_002138 | real_00279 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00279 (m n : Nat) : ∀ k, m >>> (n + k) = (m >>> n) >>> k |
| run_20260211_002138 | real_00283 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00283 [LE α] (le_refl : ∀ x : α, x ≤ x) {o : Option α} {p : α → Bool... |
| run_20260211_002138 | real_00292 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00292 {m n : Nat} : m % n.succ = m ↔ m < n.succ |

## heuristic Strict Wins

No cases.

## research Strict Exact Wins

| run | id | corruption | baseline raw/strict/exact | compared raw/strict/exact | compared reason | compared strict header |
|---|---|---|---:|---:|---|---|
| run_20260211_002138 | real_00016 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00016 {a b c : Nat} (h : a + b < c) : a < c - b |
| run_20260211_002138 | real_00036 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00036 {l : List α} {p q : α → Bool} (h : ∀ x ∈ l, p x → q x) : l.fin... |
| run_20260211_002138 | real_00040 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00040 (a b : Nat) : (NatCast.natCast (a + b : Nat) : Int) = (NatCast... |
| run_20260211_002138 | real_00058 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00058 {m n : Nat} (H : n % m = 0) : m ∣ n |
| run_20260211_002138 | real_00073 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00073 {a : Int} (b : Int) (Ha : 0 ≤ a) : a.tdiv b ≤ a |
| run_20260211_002138 | real_00097 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00097 {p : Fin 1 → Prop} : (∀ i, p i) ↔ p 0 |
| run_20260211_002138 | real_00105 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00105 {z : Int} (hz : z ≠ 0) : z.sign.natAbs = 1 |
| run_20260211_002138 | real_00134 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00134 {a b : Int} (hab : b ∣ a) : (a / b).natAbs = a.natAbs / b.natAbs |
| run_20260211_002138 | real_00138 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00138 (a : Int16) (ha : a ≠ -1) : a.toInt32 ≠ -1 |
| run_20260211_002138 | real_00141 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00141 : ∀ {b : Bool}, (b = false → b = true) ↔ (b = true) |
| run_20260211_002138 | real_00146 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00146 {a b : Prop} (h : b = True) : (a = b) = a |
| run_20260211_002138 | real_00148 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00148 (m k : Nat) : m % k = m - k * (m / k) |
| run_20260211_002138 | real_00151 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00151 {n m : Nat} (h : n ∣ m) : m / n ∣ m |
| run_20260211_002138 | real_00153 | lowercase_type | no/no/no | yes/yes/yes | - | theorem getElem!_of_getElem? [Inhabited α] : ∀ {l : List α} {i : Nat}, l[i]? = some a →... |
| run_20260211_002138 | real_00159 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00159 (b : Prop) : ¬a → ¬(a ∧ b) |
| run_20260211_002138 | real_00173 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00173 (a : Int8) : -a = -1 * a |
| run_20260211_002138 | real_00187 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00187 {p q : Prop} (hp : p) (hq : q) : HEq hp hq |
| run_20260211_002138 | real_00190 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00190 {c : Prop} {h : Decidable c} (hc : c) {α : Sort u} {t : c → α}... |
| run_20260211_002138 | real_00212 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00212 {m n : Nat} (H : m ∣ n) : n % m = 0 |
| run_20260211_002138 | real_00265 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00265 {n : Int} : -n < n ↔ 0 < n |
| run_20260211_002138 | real_00269 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00269 {a b : Int} {hab₁ hab₂} : Int8.ofIntLE (a * b) hab₁ hab₂ = Int... |
| run_20260211_002138 | real_00277 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00277 : ∀ {x y z : Bool}, (x ^^ y) = (x ^^ z) ↔ y = z |
| run_20260211_002138 | real_00279 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00279 (m n : Nat) : ∀ k, m >>> (n + k) = (m >>> n) >>> k |
| run_20260211_002138 | real_00283 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00283 [LE α] (le_refl : ∀ x : α, x ≤ x) {o : Option α} {p : α → Bool... |
| run_20260211_002138 | real_00292 | lowercase_type | no/no/no | yes/yes/yes | - | theorem bench_real_00292 {m n : Nat} : m % n.succ = m ↔ m < n.succ |

## research Raw Wins Lost By Strict Replay

| run | id | corruption | baseline raw/strict/exact | compared raw/strict/exact | compared reason | compared strict header |
|---|---|---|---:|---:|---|---|
| run_20260211_002138 | real_00111 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00111 {x y : BitVec n} : True |
| run_20260211_002138 | real_00165 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00165 : True |
| run_20260211_002138 | real_00166 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00166 (a : int8) : True |
| run_20260211_002138 | real_00188 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00188 (x : Int64) : True |
| run_20260211_002138 | real_00201 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00201 {a b : Uint16} : True |
| run_20260211_002138 | real_00260 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00260 : True |
| run_20260211_002407 | real_00000 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00000 {x y : BitVec n} : True |
| run_20260211_002407 | real_00036 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00036 {a b : Uint8} : True |
| run_20260211_002407 | real_00054 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00054 {a b c : Uint8} : True |
| run_20260211_002407 | real_00116 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00116 (c : Bool) : True |
| run_20260211_002407 | real_00131 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00131 {a b : Uint32} : True |
| run_20260211_002407 | real_00162 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00162 (x : Int16) : True |
| run_20260211_002407 | real_00297 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00297 (a b : Uint32) : True |
| run_20260211_002639 | real_00016 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00016 {w : Nat} {x : BitVec w} (hx : BitVec.sle 0#w x) : True |
| run_20260211_002639 | real_00041 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00041 (a : ISize) (ha : a ≠ minValue) : True |
| run_20260211_002639 | real_00043 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem fmod_add_fdiv' (a b : int) : True |
| run_20260211_002639 | real_00087 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00087 {a b c : Uint64} : True |
| run_20260211_002639 | real_00107 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00107 {a b c : Uint8} : True |
| run_20260211_002639 | real_00192 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00192 {x y : BitVec w} : True |
| run_20260211_002639 | real_00200 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00200 (a b : int) : True |
| run_20260211_002639 | real_00207 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00207 : True |
| run_20260211_002639 | real_00215 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00215 {x y : BitVec w} : True |
| run_20260211_002639 | real_00256 | lowercase_type | no/no/no | yes/no/no | goal_true | theorem bench_real_00256 (x : int8) : True |
| run_20260211_002138 | real_00008 | not_proposition | no/no/no | yes/no/no | goal_true | theorem bench_real_00008 {x : Option α} {p : α → Bool} (h : x.any p) : True |
| run_20260211_002138 | real_00015 | not_proposition | no/no/no | yes/no/no | goal_true | theorem bench_real_00015 (a b : Int16) (hb : b ≠ -1) : True |
