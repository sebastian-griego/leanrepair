#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Paired analysis between two policies across run directories.")
    parser.add_argument("--root", required=True, help="Directory containing run_*/ with policy jsonl files")
    parser.add_argument("--policy-a", default="heuristic", help="Baseline policy name")
    parser.add_argument("--policy-b", default="research", help="Compared policy name")
    parser.add_argument("--output-json", default="", help="Optional output JSON path")
    parser.add_argument("--output-md", default="", help="Optional output Markdown path")
    parser.add_argument("--max-failures", type=int, default=25, help="Number of failure examples to keep")
    args = parser.parse_args(argv)

    root = Path(args.root)
    run_dirs = sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("run_")])
    if not run_dirs:
        raise SystemExit(f"No run directories found under {root}")

    all_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    run_summaries: dict[str, Any] = {}
    fail_examples: list[dict[str, Any]] = []

    for run_dir in run_dirs:
        rows_a = _load_policy_rows(run_dir / f"{args.policy_a}.jsonl")
        rows_b = _load_policy_rows(run_dir / f"{args.policy_b}.jsonl")

        shared_ids = sorted(set(rows_a).intersection(rows_b))
        pairs = [(rows_a[item_id], rows_b[item_id]) for item_id in shared_ids]
        all_pairs.extend(pairs)

        paired = _paired_counts(pairs)
        run_summaries[run_dir.name] = {
            "n": len(pairs),
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

    pooled = _paired_counts(all_pairs)
    by_corruption = _paired_by_corruption(all_pairs)

    fail_examples.sort(key=lambda row: (row["corruption"], row["id"]))
    fail_examples = fail_examples[: args.max_failures]

    summary = {
        "root": str(root),
        "policy_a": args.policy_a,
        "policy_b": args.policy_b,
        "runs": run_summaries,
        "pooled": pooled,
        "by_corruption": by_corruption,
        "failure_examples": fail_examples,
    }

    output_json = Path(args.output_json) if args.output_json else root / "paired_analysis.json"
    output_md = Path(args.output_md) if args.output_md else root / "paired_analysis.md"
    output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    output_md.write_text(_to_markdown(summary), encoding="utf-8")
    print(f"Wrote {output_json} and {output_md}")
    return 0


def _load_policy_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            item_id = str(row.get("id", ""))
            rows[item_id] = row
    return rows


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


def _paired_counts(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    a_only = 0
    b_only = 0
    both = 0
    neither = 0
    for a, b in pairs:
        ok_a = bool(a.get("ok", False))
        ok_b = bool(b.get("ok", False))
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
    return {
        "n_total": total,
        "both_solve": both,
        "policy_a_only": a_only,
        "policy_b_only": b_only,
        "neither_solve": neither,
        "discordant_total": n_discordant,
        "policy_b_win_rate_on_discordant": (b_only / n_discordant) if n_discordant else 0.5,
        "paired_exact_binom_p_two_sided": p_two_sided,
    }


def _paired_by_corruption(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    buckets: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for a, b in pairs:
        corr = str(a.get("corruption", b.get("corruption", "unknown")))
        buckets.setdefault(corr, []).append((a, b))
    return {corr: _paired_counts(rows) for corr, rows in sorted(buckets.items())}


def _exact_binom_two_sided(k_extreme: int, n: int) -> float:
    if n <= 0:
        return 1.0
    # Two-sided exact binomial test under p=0.5.
    tail = 0.0
    for k in range(k_extreme, n + 1):
        tail += math.comb(n, k) * (0.5 ** n)
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
    lines = [
        "# Paired Policy Analysis",
        "",
        f"- Baseline policy: `{a}`",
        f"- Compared policy: `{b}`",
        f"- Total paired items: `{pooled['n_total']}`",
        f"- Discordant pairs: `{pooled['discordant_total']}`",
        f"- `{b}` wins on discordant pairs: `{100.0 * pooled['policy_b_win_rate_on_discordant']:.1f}%`",
        f"- Exact paired binomial p-value (two-sided): `{pooled['paired_exact_binom_p_two_sided']:.3e}`",
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
        "| Corruption | N | Baseline Only | Compared Only | p-value |",
        "|---|---:|---:|---:|---:|",
    ]
    for corr, row in summary["by_corruption"].items():
        lines.append(
            f"| {corr} | {row['n_total']} | {row['policy_a_only']} | {row['policy_b_only']} | "
            f"{row['paired_exact_binom_p_two_sided']:.3e} |"
        )

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
