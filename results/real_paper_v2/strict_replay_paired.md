# LeanRepair Strict Replay Paired Analysis

- Baseline policy: `heuristic`
- Compared policy: `research`
- Paired records: `900`
- Unpaired records: `0` heuristic-only, `0` research-only
- Raw solve lift: `+74.0 pp` (research only `666`, heuristic only `0`)
- Strict solve lift: `+27.8 pp` (research only `252`, heuristic only `2`)
- Strict exact lift: `+27.7 pp` (research only `249`, heuristic only `0`)
- Strict solve sign-test p-value: `2.238e-72`
- Strict exact sign-test p-value: `2.211e-75`

## Metric Table

| Metric | Both | Baseline only | Compared only | Neither | Baseline rate | Compared rate | Lift | p-value |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `raw_ok` | 90 | 0 | 666 | 144 | 10.0% | 84.0% | +74.0 pp | 6.532e-201 |
| `strict_ok` | 3 | 2 | 252 | 643 | 0.6% | 28.3% | +27.8 pp | 2.238e-72 |
| `strict_exact` | 0 | 0 | 249 | 651 | 0.0% | 27.7% | +27.7 pp | 2.211e-75 |

## Policy Strictness

| Policy | Raw solved | Strict solved | Strict exact | Raw degenerate | Lost under strict | Strict retention |
|---|---:|---:|---:|---:|---:|---:|
| `heuristic` | 90 | 5 | 0 | 85 | 85 | 5.6% |
| `research` | 756 | 255 | 249 | 501 | 501 | 33.7% |

## By Corruption

| Corruption | N | Strict baseline only | Strict compared only | Strict lift | Strict exact lift | Strict p-value |
|---|---:|---:|---:|---:|---:|---:|
| `lowercase_type` | 118 | 0 | 84 | +71.2 pp | +71.2 pp | 1.034e-25 |
| `not_proposition` | 194 | 0 | 0 | +0.0 pp | +0.0 pp | 1.000e+00 |
| `parse_missing_colon` | 176 | 0 | 91 | +51.7 pp | +50.6 pp | 8.078e-28 |
| `parse_unbalanced_paren` | 143 | 2 | 71 | +48.3 pp | +49.7 pp | 5.722e-19 |
| `type_mismatch` | 140 | 0 | 0 | +0.0 pp | +0.0 pp | 1.000e+00 |
| `unknown_type_symbol` | 129 | 0 | 6 | +4.7 pp | +3.9 pp | 3.125e-02 |

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

| run | id | corruption | baseline raw/strict/exact | compared raw/strict/exact | compared reason | compared strict header |
|---|---|---|---:|---:|---|---|
| run_20260211_002639 | real_00066 | parse_unbalanced_paren | yes/yes/no | yes/no/no | goal_true | theorem bench_real_00066 {n d : Nat} : True |
| run_20260211_002639 | real_00288 | parse_unbalanced_paren | yes/yes/no | yes/no/no | goal_true | theorem bench_real_00288 [Decidable a] : True |

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
