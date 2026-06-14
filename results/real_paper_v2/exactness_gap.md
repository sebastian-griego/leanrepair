# LeanRepair Exactness Gap

- Root: `results\real_paper_v2`
- Policies: `heuristic, research`

## Aggregate

| Policy | Records | Solved | Exact | Drift | Solve Rate | Exact Rate | Solve-Exact Gap | Exact Given Solved | Drift Given Solved | Avg Header Similarity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| heuristic | 900 | 90 | 0 | 90 | 10.0% | 0.0% | 10.0% | 0.0% | 100.0% | 61.3% |
| research | 900 | 756 | 249 | 507 | 84.0% | 27.7% | 56.3% | 32.9% | 67.1% | 76.0% |

## By Corruption

### heuristic

| Corruption | N | Solve Rate | Exact Rate | Exact Given Solved | Avg Similarity |
|---|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 0.0% | 0.0% | 0.0% | - |
| not_proposition | 194 | 44.3% | 0.0% | 0.0% | 61.2% |
| parse_missing_colon | 176 | 0.0% | 0.0% | 0.0% | - |
| parse_unbalanced_paren | 143 | 1.4% | 0.0% | 0.0% | 71.5% |
| type_mismatch | 140 | 1.4% | 0.0% | 0.0% | 55.3% |
| unknown_type_symbol | 129 | 0.0% | 0.0% | 0.0% | - |

### research

| Corruption | N | Solve Rate | Exact Rate | Exact Given Solved | Avg Similarity |
|---|---:|---:|---:|---:|---:|
| lowercase_type | 118 | 90.7% | 71.2% | 78.5% | 91.4% |
| not_proposition | 194 | 95.4% | 0.0% | 0.0% | 68.0% |
| parse_missing_colon | 176 | 69.3% | 50.6% | 73.0% | 84.9% |
| parse_unbalanced_paren | 143 | 88.8% | 49.7% | 55.9% | 79.9% |
| type_mismatch | 140 | 97.1% | 0.0% | 0.0% | 71.0% |
| unknown_type_symbol | 129 | 61.2% | 3.9% | 6.3% | 62.4% |

## Largest Solved-Not-Exact Drifts

### heuristic

| id | corruption | similarity | final header | target header |
|---|---|---:|---|---|
| real_00136 | not_proposition | 31.0% | theorem bench_real_00136 : Nat = Nat | theorem bench_real_00136 : ∀ {o₁ o₂ : Ordering}, (o₁.then o₂).isGT = (o₁.isGT \|\| o₁.isEq && o₂.isGT) |
| real_00010 | not_proposition | 36.0% | theorem bench_real_00010 : Nat = Nat | theorem bench_real_00010 : ∀ (x y z : Bool), (x && (y ^^ z)) = ((x && y) ^^ (x && z)) |
| real_00077 | not_proposition | 36.9% | theorem bench_real_00077 : Nat = Nat | theorem bench_real_00077 : ∀ (x y z : Bool), (x \|\| y && z) = ((x \|\| y) && (x \|\| z)) |
| real_00091 | not_proposition | 39.5% | theorem bench_real_00091 : Nat = Nat | theorem bench_real_00091 : ∀ {o₁ o₂ : Ordering}, (o₁.then o₂).isGE → o₁.isGE |
| real_00098 | not_proposition | 40.0% | theorem bench_real_00098 : Nat = Nat | theorem bench_real_00098 : ∀ {x y : Bool}, (x \|\| y) = true ↔ x = true ∨ y = true |
| real_00209 | not_proposition | 40.5% | theorem bench_real_00209 : Nat = Nat | theorem bench_real_00209 : ∀ {a b c : Int}, a ∣ b → b ∣ c → b.fdiv a ∣ c.fdiv a |
| real_00272 | not_proposition | 42.7% | theorem bench_real_00272 : Nat = Nat | theorem bench_real_00272 : (a :: l)[i]? = if i = 0 then some a else l[i-1]? |
| real_00185 | not_proposition | 43.8% | theorem bench_real_00185 : Nat = Nat | theorem bench_real_00185 : {x y : Int8} → x.toBitVec = y.toBitVec → x = y |
| real_00120 | not_proposition | 44.3% | theorem bench_real_00120 : Nat = Nat | theorem bench_real_00120 : (a ^^^ b) / 2 ^ n = a / 2 ^ n ^^^ b / 2 ^ n |
| real_00266 | not_proposition | 44.8% | theorem bench_real_00266 : Nat = Nat | theorem bench_real_00266 : o.join = none ↔ o = none ∨ o = some none |

### research

| id | corruption | similarity | final header | target header |
|---|---|---:|---|---|
| real_00254 | parse_unbalanced_paren | 22.4% | theorem bench_real_00254 : True | theorem bench_real_00254 (a b : UInt64) (ha : a < 4294967296) (hb : b < 4294967296) : (a % b).toUSize = a.toUSize % b... |
| real_00210 | parse_missing_colon | 22.7% | theorem any_eq' : True | theorem any_eq' {xs : Vector α n} {p : α → Bool} : xs.any p = decide (∃ x, x ∈ xs ∧ p x) |
| real_00030 | parse_missing_colon | 25.4% | theorem bench_real_00030 : True | theorem bench_real_00030 {α : Sort u} {β : α → Sort v} {f g : (x : α) → β x} (h : Eq f g) (a : α) : Eq (f a) (g a) |
| real_00044 | parse_unbalanced_paren | 26.2% | theorem bench_real_00044 : True | theorem bench_real_00044 (x : BitVec w) (i : Nat) : x.getLsbD i = (decide (i < w) && x.getMsbD (w - 1 - i)) |
| real_00182 | parse_missing_colon | 26.2% | theorem bench_real_00182 : True | theorem bench_real_00182 (x : BitVec w) (i : Nat) : x.getMsbD i = (decide (i < w) && x.getLsbD (w - 1 - i)) |
| real_00161 | unknown_type_symbol | 27.3% | theorem bench_real_00161 (a b : Foo) : True | theorem bench_real_00161 (a b : Nat) : (NatCast.natCast (a * b : Nat) : Int) = (NatCast.natCast a : Int) * (NatCast.n... |
| real_00115 | parse_missing_colon | 27.6% | theorem bench_real_00115 : True | theorem bench_real_00115 (a c : Nat) {b d : Nat} (h : b ≤ d) : (a + b ≤ c + d) = (a ≤ c + (d - b)) |
| real_00217 | parse_missing_colon | 27.8% | theorem bench_real_00217 : True | theorem bench_real_00217 (x n p : Nat) (h₁ : x < n*p) : (n * p - (x + 1)) / n = p - ((x / n) + 1) |
| real_00083 | parse_missing_colon | 30.1% | theorem bench_real_00083 : True | theorem bench_real_00083 {w : Nat} {x : BitVec w} (h : x.msb = false) : x.toNat < 2 ^ (w - 1) |
| real_00022 | type_mismatch | 30.6% | theorem bench_real_00022 : True | theorem bench_real_00022 : (a::as).find? p = match p a with \| true => some a \| false => as.find? p |

