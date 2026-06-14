#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jsonl_io import load_jsonl_map_by_key  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Paired analysis between two policies across run directories."
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Directory containing run_*/ with policy jsonl files",
    )
    parser.add_argument("--policy-a", default="heuristic", help="Baseline policy name")
    parser.add_argument("--policy-b", default="research", help="Compared policy name")
    parser.add_argument("--output-json", default="", help="Optional output JSON path")
    parser.add_argument("--output-md", default="", help="Optional output Markdown path")
    parser.add_argument(
        "--max-failures",
        type=int,
        default=25,
        help="Number of failure examples to keep",
    )
    parser.add_argument(
        "--strict-pairs",
        action="store_true",
        help="Fail if a run has records for only one policy",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=2000,
        help="Bootstrap samples for paired lift CIs",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for bootstrap confidence intervals",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    run_dirs = sorted(
        [p for p in root.iterdir() if p.is_dir() and p.name.startswith("run_")]
    )
    if not run_dirs:
        raise SystemExit(f"No run directories found under {root}")

    all_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    run_summaries: dict[str, Any] = {}
    fail_examples: list[dict[str, Any]] = []
    pooled_coverage = {
        "policy_a_records": 0,
        "policy_b_records": 0,
        "paired_records": 0,
        "policy_a_unpaired": 0,
        "policy_b_unpaired": 0,
    }

    for run_index, run_dir in enumerate(run_dirs):
        rows_a = _load_policy_rows(run_dir / f"{args.policy_a}.jsonl")
        rows_b = _load_policy_rows(run_dir / f"{args.policy_b}.jsonl")

        coverage = _coverage_counts(rows_a, rows_b)
        for key in pooled_coverage:
            pooled_coverage[key] += coverage[key]
        if args.strict_pairs and (
            coverage["policy_a_unpaired"] or coverage["policy_b_unpaired"]
        ):
            raise SystemExit(
                f"Unpaired rows in {run_dir}: "
                f"{args.policy_a}-only={coverage['policy_a_unpaired']}, "
                f"{args.policy_b}-only={coverage['policy_b_unpaired']}"
            )

        shared_ids = sorted(set(rows_a).intersection(rows_b))
        pairs = [(rows_a[item_id], rows_b[item_id]) for item_id in shared_ids]
        all_pairs.extend(pairs)

        paired = _paired_counts(
            pairs,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed + run_index,
        )
        run_summaries[run_dir.name] = {
            "n": len(pairs),
            "coverage": coverage,
            "paired": paired,
            "policy_a_solve_rate": _solve_rate(rows_a.values()),
            "policy_b_solve_rate": _solve_rate(rows_b.values()),
            "policy_a_exact_rate": _exact_rate(rows_a.values()),
            "policy_b_exact_rate": _exact_rate(rows_b.values()),
        }

        for a, b in pairs:
            if not b.get("ok", False):
                fail_examples.append(
                    {
                        "run": run_dir.name,
                        "id": b.get("id"),
                        "corruption": b.get("corruption", "unknown"),
                        "candidate0": b.get("candidate0", ""),
                        "target": b.get("target", ""),
                        "final": b.get("final", ""),
                        "errors": _last_error_messages(b.get("trace", [])),
                    }
                )

    pooled = _paired_counts(
        all_pairs,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    by_corruption = _paired_by_corruption(
        all_pairs,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )

    fail_examples.sort(key=lambda row: (row["corruption"], row["id"]))
    fail_examples = fail_examples[: args.max_failures]

    summary = {
        "root": str(root),
        "policy_a": args.policy_a,
        "policy_b": args.policy_b,
        "runs": run_summaries,
        "coverage": pooled_coverage,
        "pooled": pooled,
        "by_corruption": by_corruption,
        "failure_examples": fail_examples,
        "bootstrap_samples": args.bootstrap_samples,
        "bootstrap_seed": args.seed,
    }

    output_json = (
        Path(args.output_json) if args.output_json else root / "paired_analysis.json"
    )
    output_md = Path(args.output_md) if args.output_md else root / "paired_analysis.md"
    output_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    output_md.write_text(_to_markdown(summary), encoding="utf-8")
    print(f"Wrote {output_json} and {output_md}")
    return 0


def _load_policy_rows(path: Path) -> dict[str, dict[str, Any]]:
    return load_jsonl_map_by_key(path, "id")


def _solve_rate(rows: Any) -> float:
    rows = list(rows)
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get("ok", False)) / len(rows)


def _exact_rate(rows: Any) -> float:
    rows = list(rows)
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get("exact", False)) / len(rows)


def _coverage_counts(rows_a: dict[str, Any], rows_b: dict[str, Any]) -> dict[str, int]:
    ids_a = set(rows_a)
    ids_b = set(rows_b)
    return {
        "policy_a_records": len(ids_a),
        "policy_b_records": len(ids_b),
        "paired_records": len(ids_a.intersection(ids_b)),
        "policy_a_unpaired": len(ids_a - ids_b),
        "policy_b_unpaired": len(ids_b - ids_a),
    }


def _paired_counts(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    bootstrap_samples: int = 0,
    seed: int = 0,
) -> dict[str, Any]:
    a_only = 0
    b_only = 0
    both = 0
    neither = 0
    a_exact = 0
    b_exact = 0
    for a, b in pairs:
        ok_a = bool(a.get("ok", False))
        ok_b = bool(b.get("ok", False))
        a_exact += int(bool(a.get("exact", False)))
        b_exact += int(bool(b.get("exact", False)))
        if ok_a and ok_b:
            both += 1
        elif ok_a and not ok_b:
            a_only += 1
        elif ok_b and not ok_a:
            b_only += 1
        else:
            neither += 1

    n_discordant = a_only + b_only
    if n_discordant > 0:
        p_two_sided = _exact_binom_two_sided(max(a_only, b_only), n_discordant)
    else:
        p_two_sided = 1.0

    total = len(pairs)
    a_solved = both + a_only
    b_solved = both + b_only
    solve_lift = _paired_lift(pairs, "ok")
    exact_lift = _paired_lift(pairs, "exact")
    solve_lift_ci = _bootstrap_lift_ci(
        pairs, "ok", samples=bootstrap_samples, seed=seed
    )
    exact_lift_ci = _bootstrap_lift_ci(
        pairs, "exact", samples=bootstrap_samples, seed=seed + 1009
    )
    return {
        "n_total": total,
        "both_solve": both,
        "policy_a_only": a_only,
        "policy_b_only": b_only,
        "neither_solve": neither,
        "policy_a_solved": a_solved,
        "policy_b_solved": b_solved,
        "policy_a_solve_rate": (a_solved / total) if total else 0.0,
        "policy_b_solve_rate": (b_solved / total) if total else 0.0,
        "policy_a_exact_rate": (a_exact / total) if total else 0.0,
        "policy_b_exact_rate": (b_exact / total) if total else 0.0,
        "policy_b_solve_lift": solve_lift,
        "policy_b_solve_lift_ci95": solve_lift_ci,
        "policy_b_exact_lift": exact_lift,
        "policy_b_exact_lift_ci95": exact_lift_ci,
        "discordant_total": n_discordant,
        "policy_b_win_rate_on_discordant": (
            (b_only / n_discordant) if n_discordant else 0.5
        ),
        "paired_exact_binom_p_two_sided": p_two_sided,
    }


def _paired_by_corruption(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    bootstrap_samples: int = 0,
    seed: int = 0,
) -> dict[str, Any]:
    buckets: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for a, b in pairs:
        corr = str(a.get("corruption", b.get("corruption", "unknown")))
        buckets.setdefault(corr, []).append((a, b))
    return {
        corr: _paired_counts(
            rows,
            bootstrap_samples=bootstrap_samples,
            seed=seed + sum(ord(ch) for ch in corr),
        )
        for corr, rows in sorted(buckets.items())
    }


def _paired_lift(pairs: list[tuple[dict[str, Any], dict[str, Any]]], key: str) -> float:
    if not pairs:
        return 0.0
    total = 0
    for a, b in pairs:
        total += int(bool(b.get(key, False))) - int(bool(a.get(key, False)))
    return total / len(pairs)


def _bootstrap_lift_ci(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    key: str,
    *,
    samples: int,
    seed: int,
) -> list[float]:
    if not pairs:
        return [0.0, 0.0]
    estimate = _paired_lift(pairs, key)
    if samples <= 0:
        return [estimate, estimate]

    rng = random.Random(seed)
    n = len(pairs)
    lifts: list[float] = []
    deltas = [
        int(bool(b.get(key, False))) - int(bool(a.get(key, False))) for a, b in pairs
    ]
    for _ in range(samples):
        lifts.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    lifts.sort()
    return [_percentile(lifts, 0.025), _percentile(lifts, 0.975)]


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return values[0]
    if q >= 1:
        return values[-1]
    pos = q * (len(values) - 1)
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return values[low]
    weight = pos - low
    return values[low] * (1.0 - weight) + values[high] * weight


def _exact_binom_two_sided(k_extreme: int, n: int) -> float:
    if n <= 0:
        return 1.0
    # Two-sided exact binomial test under p=0.5.
    tail = 0.0
    for k in range(k_extreme, n + 1):
        tail += math.comb(n, k) * (0.5**n)
    return min(1.0, 2.0 * tail)


def _last_error_messages(trace: list[dict[str, Any]]) -> list[str]:
    if not trace:
        return []
    last = trace[-1]
    errors = last.get("errors", [])
    return [str(err.get("message", "")) for err in errors[:3]]


def _to_markdown(summary: dict[str, Any]) -> str:
    a = summary["policy_a"]
    b = summary["policy_b"]
    pooled = summary["pooled"]
    coverage = summary["coverage"]
    solve_ci = pooled["policy_b_solve_lift_ci95"]
    exact_ci = pooled["policy_b_exact_lift_ci95"]
    lines = [
        "# Paired Policy Analysis",
        "",
        f"- Baseline policy: `{a}`",
        f"- Compared policy: `{b}`",
        f"- Total paired items: `{pooled['n_total']}`",
        f"- Unpaired records: `{coverage['policy_a_unpaired']}` {a}-only, "
        f"`{coverage['policy_b_unpaired']}` {b}-only",
        f"- Discordant pairs: `{pooled['discordant_total']}`",
        f"- `{b}` wins on discordant pairs: `{100.0 * pooled['policy_b_win_rate_on_discordant']:.1f}%`",
        f"- `{b}` solve-rate lift: `{100.0 * pooled['policy_b_solve_lift']:.1f}` percentage points "
        f"(bootstrap 95% CI `{100.0 * solve_ci[0]:.1f}`, `{100.0 * solve_ci[1]:.1f}`)",
        f"- `{b}` exact-rate lift: `{100.0 * pooled['policy_b_exact_lift']:.1f}` percentage points "
        f"(bootstrap 95% CI `{100.0 * exact_ci[0]:.1f}`, `{100.0 * exact_ci[1]:.1f}`)",
        f"- Exact paired binomial p-value (two-sided): `{pooled['paired_exact_binom_p_two_sided']:.3e}`",
        "",
        "## Coverage",
        "",
        "| Policy | Records | Unpaired |",
        "|---|---:|---:|",
        f"| {a} | {coverage['policy_a_records']} | {coverage['policy_a_unpaired']} |",
        f"| {b} | {coverage['policy_b_records']} | {coverage['policy_b_unpaired']} |",
        f"| paired | {coverage['paired_records']} | 0 |",
        "",
        "## Pooled Outcomes",
        "",
        "| Outcome | Count |",
        "|---|---:|",
        f"| both solve | {pooled['both_solve']} |",
        f"| {a} only | {pooled['policy_a_only']} |",
        f"| {b} only | {pooled['policy_b_only']} |",
        f"| neither solve | {pooled['neither_solve']} |",
        "",
        "## By Corruption",
        "",
        "| Corruption | N | Baseline Only | Compared Only | Solve Lift | 95% CI | p-value |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for corr, row in summary["by_corruption"].items():
        corr_ci = row["policy_b_solve_lift_ci95"]
        lines.append(
            f"| {corr} | {row['n_total']} | {row['policy_a_only']} | {row['policy_b_only']} | "
            f"{100.0 * row['policy_b_solve_lift']:.1f} pp | "
            f"[{100.0 * corr_ci[0]:.1f}, {100.0 * corr_ci[1]:.1f}] | "
            f"{row['paired_exact_binom_p_two_sided']:.3e} |"
        )

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
