# LeanRepair

An automated repair system for Lean theorem proving code. LeanRepair implements an iterative refinement loop that attempts to fix malformed or incorrect Lean theorem declarations by parsing compiler errors and applying repair strategies.

## Overview

LeanRepair takes incomplete or incorrect Lean theorem/lemma declarations and:

1. Validates them by running the Lean compiler
2. Parses compilation errors and classifies them
3. Applies heuristic or LLM-based policies to suggest fixes
4. Repeats until the theorem passes type-checking or max iterations are reached

## Requirements

- Python 3.10+
- Lean 4 with Lake (for theorem validation)
- Optional: OpenAI API key (for LLM-based repair policy)

## Installation

```bash
git clone https://github.com/sebastian-griego/leanrepair.git
cd leanrepair
pip install -r requirements.txt
```

Ensure Lean 4 is installed and `lake env lean` is available in your PATH.

## Usage

### Command Line Interface

Process a JSONL dataset of theorems:

```bash
python repair_cli.py \
    --input dataset.jsonl \
    --output results.jsonl \
    --Tmax 6 \
    --timeout-s 20 \
    --policy research \
    --acceptance strict
```

#### Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--input` | Path to input JSONL file | Required |
| `--output` | Path to output JSONL file | Required |
| `--Tmax` | Maximum repair iterations per theorem | 3 |
| `--timeout-s` | Lean compiler timeout in seconds | 20.0 |
| `--policy` | Repair policy: `heuristic`, `research`, `research_strict`, or `openai` | heuristic |
| `--acceptance` | Acceptance rule: `lean_ok` accepts any typechecking candidate; `strict` rejects degenerate typechecking candidates such as `True` goals and reflexive equalities | lean_ok |
| `--token-recall-floor` | Minimum target-token recall for strict acceptance | 0.2 |
| `--skip-invalid-rows` | Skip malformed or non-object JSONL rows instead of failing before output is written | false |

### Input Format

Input JSONL files should contain records with the following fields:

```json
{"id": "theorem_1", "nl": "Natural language description", "ctx": "import Mathlib\n\n", "candidate": "theorem foo : Nat"}
```

The CLI validates the JSONL before writing results. Malformed rows or non-object
rows stop the run with a line-numbered error; use `--skip-invalid-rows` only for
ad hoc cleanup runs where dropping bad rows is intentional.

| Field | Description |
|-------|-------------|
| `id` | Unique identifier for the theorem |
| `nl` | Natural language description of the theorem |
| `ctx` | Lean context (imports, definitions, etc.) |
| `candidate` | The theorem declaration to repair |

### Output Format

Output JSONL contains:

```json
{
  "id": "theorem_1",
  "ok": true,
  "acceptance": "lean_ok",
  "final": "theorem foo : Nat := by sorry",
  "steps": 2,
  "trace": [...]
}
```

## Policies

### Heuristic Policy

The baseline heuristic policy applies rule-based repairs for common error patterns:

- **Unknown identifier**: Adds type-annotated binders (e.g., `(x : Type)`)
- **Parse errors**: Truncates unbalanced brackets, simplifies expressions
- **Type mismatches**: Ensures binders have explicit type annotations

### Research Policy

`research` is a stronger multi-candidate policy designed for evaluation:

- Expands each failing step into multiple repair candidates (search instead of single rewrite)
- Handles extra error modes, including non-proposition theorem goals
- Applies syntax repairs for missing top-level `:` and unbalanced binder parentheses
- Repairs common corruption patterns (`nat` -> `Nat`, `x = True` -> `x = x`, inferred type replacement for unknown type symbols)

Use `research_strict` to run the same search without trivial `True` and reflexive-equality fallback proposals. Use `--acceptance strict` when LeanRepair should also reject any degenerate Lean-ok candidate during the repair loop and continue to later queued candidates when available.

### OpenAI Policy

Uses OpenAI's API to generate repairs:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-4"

python repair_cli.py --input data.jsonl --output out.jsonl --policy openai
```

Environment variables:
- `OPENAI_API_KEY`: API key (required for openai policy)
- `OPENAI_MODEL`: Model to use (required for openai policy)
- `OPENAI_BASE_URL`: Custom API endpoint (default: https://api.openai.com/v1)
- `OPENAI_ORG`: Organization ID (optional)
- `OPENAI_PROJECT`: Project ID (optional)

The OpenAI policy falls back to heuristic repairs if the API is unavailable or returns invalid responses.
When a model returns a Lean code block with imports or a proof body, LeanRepair extracts the theorem/lemma header and then runs the same sanitizer used by the local policies.

## Research Workflow

### Synthetic Benchmark (Controlled Corruptions)

Generate a deterministic synthetic benchmark and run evaluations:

```bash
python scripts/generate_benchmark.py \
  --output data/synth_benchmark.jsonl \
  --num-items 300 \
  --seed 7

python scripts/run_experiments.py \
  --input data/synth_benchmark.jsonl \
  --output-dir results \
  --policies heuristic research \
  --Tmax 6 \
  --timeout-s 25 \
  --warmup
```

Experiment inputs are validated before any run directory is created. Each
benchmark row must contain non-empty string `id`, `candidate`, and `target`
fields; optional `nl`, `ctx`, and `corruption` fields must also be strings when
present. Schema errors report the physical JSONL line number.

### Real Benchmark (Mined from Lean Source)

Build a real benchmark by mining theorem/lemma headers from local Lean sources (`Init`/`Std`), validating clean targets, and keeping only corrupted variants that fail Lean checking:

```bash
python scripts/build_real_benchmark.py \
  --output data/real_benchmark_seed7.jsonl \
  --num-items 300 \
  --seed 7 \
  --timeout-s 25

python scripts/run_experiments.py \
  --input data/real_benchmark_seed7.jsonl \
  --output-dir results/real_paper \
  --policies heuristic research \
  --Tmax 6 \
  --timeout-s 25 \
  --acceptance lean_ok \
  --warmup
```

For a 3-seed study:

```bash
for s in 7 17 27; do
  python scripts/build_real_benchmark.py --output data/real_benchmark_seed${s}.jsonl --num-items 300 --seed ${s} --timeout-s 25
  python scripts/run_experiments.py --input data/real_benchmark_seed${s}.jsonl --output-dir results/real_paper --policies heuristic research --Tmax 6 --timeout-s 25 --warmup
done

python scripts/analyze_paired_results.py --root results/real_paper --policy-a heuristic --policy-b research
python scripts/analyze_trace_taxonomy.py --root results/real_paper --policies heuristic research
python scripts/analyze_budget_curve.py --root results/real_paper --policies heuristic research
python scripts/analyze_exactness_gap.py --root results/real_paper --policies heuristic research
python scripts/analyze_semantic_drift.py --root results/real_paper --policies heuristic research
python scripts/analyze_quality_summary.py --root results/real_paper --policies heuristic research
python scripts/analyze_strict_replay.py --root results/real_paper --policies heuristic research
python scripts/analyze_strict_replay_casebook.py --root results/real_paper --policies heuristic research
python scripts/analyze_strict_replay_paired.py --records-jsonl results/real_paper/strict_replay_records.jsonl --policy-a heuristic --policy-b research
```

The paired analyzer reports coverage before comparing policies, so unmatched
rows are visible instead of being silently dropped. Use `--strict-pairs` to
fail a run with missing policy outputs, and tune `--bootstrap-samples`/`--seed`
to reproduce confidence intervals for solve-rate and exact-rate lift. Per-policy
result files are loaded through duplicate-`id` checks across the aggregate
analyzers, with physical line numbers in failures, so accidental concatenation
cannot silently inflate or overwrite reported results.
Strict replay ledgers are schema-validated when loaded from JSONL and reject
duplicate `(run, id, policy)` rows with the physical line number, so the
casebook and paired replay reports cannot double-count a replay decision from a
corrupted or resumed ledger.

Experiment artifacts are written under `results/<group>/run_<timestamp>/`:

- Per-policy traces: `heuristic.jsonl`, `research.jsonl`
- Aggregates: `summary.json`, `<policy>.summary.json`
- Table-ready report: `report.md`
- Trace taxonomy: `trace_taxonomy.json`, `trace_taxonomy.md`
- Repair budget curve: `budget_curve.json`, `budget_curve.md`
- Exactness gap: `exactness_gap.json`, `exactness_gap.md`
- Semantic drift audit: `semantic_drift.json`, `semantic_drift.md`
- Quality-adjusted summary: `quality_summary.json`, `quality_summary.md`
- Strict replay audit: `strict_replay.json`, `strict_replay.md`, `strict_replay_records.jsonl`
- Strict replay casebook: `strict_replay_casebook.json`, `strict_replay_casebook.md`, `strict_replay_casebook_cases.jsonl`
- Strict replay paired comparison: `strict_replay_paired.json`, `strict_replay_paired.md`

Trace taxonomy reports are acceptance-aware: on strict-acceptance runs they
separate raw Lean-ok candidates from candidates actually accepted by the repair
loop, and count rejection reasons such as `goal_true`.

### Current Snapshot (Real Data v2, 3 Seeds, 300 Items/Seed)

- Generated snapshot: `results/real_paper_v2/snapshot_summary.md`
- Snapshot rollup includes aggregate outcomes, repair-budget curve, exactness
  gap, quality adjustment, trace taxonomy, strict replay, and paired replay
  with source paths and SHA-256 provenance for the exact component artifacts.
- Aggregate report: `results/real_paper_v2/aggregate_report.md`
- Quality-adjusted report: `results/real_paper_v2/quality_summary.md`
- Baseline `heuristic`: solve rate `10.0% +/- 1.2%`, exact rate `0.0% +/- 0.0%`
- `research`: solve rate `84.0% +/- 1.1%`, exact rate `27.7% +/- 3.1%`
- Pooled across all 900 items:
- `heuristic` solve `10.0%` (95% CI `[8.2, 12.1]`)
- `research` solve `84.0%` (95% CI `[81.5, 86.2]`)
- Paired test (`research` vs `heuristic`): exact two-sided binomial `p = 6.532e-201`
- Semantic drift audit: `research` has `504/756` solved outputs classified as degenerate (`338` `True` goals, `157` reflexive equalities, `9` bare-identifier goals), leaving `252/900` nondegenerate solved headers; the same stricter classifier marks all `90` heuristic solves as degenerate.
- Strict replay audit: filtering degenerate accepted fixes preserves all `251` exact `research` repairs while reducing raw `research` solves from `756/900` to `252/900`; `251/252` strict accepted repairs are exact, with only one nondegenerate-but-nonexact accept. `results/real_paper_v2/strict_replay_records.jsonl` contains the 1,800 row-level replay decisions behind the aggregate report.
- Strict replay casebook: `results/real_paper_v2/strict_replay_casebook.md` extracts `595` focused rows from the replay ledger (`594` raw solves lost under strict replay and `1` strict nonexact accept), with loss reasons split into `338` `goal_true`, `235` reflexive equalities, and `21` bare-identifier goals.
- Strict paired replay: `results/real_paper_v2/strict_replay_paired.md` shows that the raw `research` solve lift of `+74.0` percentage points becomes a strict solve lift of `+28.0` points (`252` `research`-only strict solves vs `0` `heuristic`-only; sign-test `p = 2.764e-76`) and a strict exact lift of `+27.9` points (`251` `research`-only exact repairs vs `0`; `p = 5.527e-76`). It also identifies `414` raw `research`-only wins that strict replay rejects as degenerate, now split by rejection reason (`334` `goal_true`, `80` `reflexive_equality`) and corruption type.

Per-run artifacts are available under `results/real_paper_v2/run_*/`.

Regenerate the compact source-traceable snapshot after refreshing component
reports:

```bash
python scripts/summarize_real_paper_snapshot.py --root results/real_paper_v2
```

Run the full local reproducibility gate used by CI:

```bash
python scripts/verify_reproducibility.py
```

With `make` available, the equivalent shortcut is:

```bash
make verify
```

Write a machine-readable command report:

```bash
python scripts/verify_reproducibility.py --report-json results/reproducibility_report.json
```

With `make` available:

```bash
make verify-report
```

The JSON report records `schema_version`, planned and executed command counts,
per-command return codes, elapsed times, and the first failed command when the
gate stops early.

CI uploads this report as an artifact for each supported Python version.

Verify the checked-in snapshot is current without rewriting it:

```bash
python scripts/summarize_real_paper_snapshot.py --root results/real_paper_v2 --check
```

With `make` available:

```bash
make snapshot-check
```

Verify that the source hashes embedded in the checked-in snapshot still match
the current component artifacts:

```bash
python scripts/summarize_real_paper_snapshot.py \
  --output-json results/real_paper_v2/snapshot_summary.json \
  --verify-source-hashes
```

With `make` available:

```bash
make source-hashes
```

## API Usage

```python
from src.repair_loop import repair_one, default_policy
from src.lean_check import lean_check, sanitize_candidate, build_theorem

# Repair a single theorem
trace = repair_one(
    nl="A theorem about natural numbers",
    ctx="",
    candidate0="theorem foo : nat",
    Tmax=3,
    timeout_s=2.0,
    policy=default_policy,
)

print(f"Success: {trace.steps[-1].result.ok}")
print(f"Final: {trace.steps[-1].candidate}")
```

## Error Classification

LeanRepair classifies Lean compiler errors into categories:

| Category | Example Patterns |
|----------|-----------------|
| `unknown_identifier` | "unknown identifier", "unknown constant" |
| `not_proposition` | "is not a proposition", "expected proposition" |
| `type_mismatch` | "type mismatch", "expected type" |
| `failed_typeclass` | "failed to synthesize", "typeclass" |
| `parse_error` | "unexpected token", "parse error" |
| `notation_scope` | "unknown notation", "invalid notation" |
| `other` | Unclassified errors |

## Project Structure

```
leanrepair/
├── repair_cli.py          # CLI entry point
├── scripts/
│   ├── build_real_benchmark.py  # Real benchmark builder from Lean source
│   ├── analyze_paired_results.py # Paired policy significance analysis
│   ├── generate_benchmark.py   # Synthetic benchmark generator
│   └── run_experiments.py      # Multi-policy experiment runner
├── src/
│   ├── lean_check.py      # Lean compiler interaction
│   ├── lean_errors.py     # Error parsing and classification
│   ├── repair_loop.py     # Core repair iteration logic
│   ├── llm_policy.py      # Policy backends (heuristic/research/OpenAI)
│   └── eval_utils.py      # Metrics + confidence intervals
├── tests/
│   └── *.py               # Unit tests
└── requirements.txt       # Python dependencies
```

## Testing

```bash
pip install pytest
python -m pytest tests/ -v
```

CI runs the unit tests on supported Python versions. The tests mock Lean calls
where possible so they can exercise repair logic without requiring API keys.

## License

MIT License
