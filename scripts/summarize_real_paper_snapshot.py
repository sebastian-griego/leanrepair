#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ARTIFACTS = {
    "aggregate": "aggregate_summary.json",
    "budget_curve": "budget_curve.json",
    "exactness_gap": "exactness_gap.json",
    "quality": "quality_summary.json",
    "semantic_drift": "semantic_drift.json",
    "strict_replay": "strict_replay.json",
    "strict_casebook": "strict_replay_casebook.json",
    "strict_paired": "strict_replay_paired.json",
    "trace_taxonomy": "trace_taxonomy.json",
}


def build_snapshot(root: Path) -> dict[str, Any]:
    root = Path(root)
    source_paths = {name: root / filename for name, filename in ARTIFACTS.items()}
    loaded = {name: _load_json(path) for name, path in source_paths.items()}
    aggregate = loaded["aggregate"]
    budget = loaded["budget_curve"]
    exactness = loaded["exactness_gap"]
    quality = loaded["quality"]
    semantic = loaded["semantic_drift"]
    strict = loaded["strict_replay"]
    casebook = loaded["strict_casebook"]
    paired = loaded["strict_paired"]
    trace = loaded["trace_taxonomy"]

    policies = sorted(aggregate["policies"])
    return {
        "root": str(root).replace("\\", "/"),
        "provenance": {
            "generator": "scripts/summarize_real_paper_snapshot.py",
            "sources": {
                name: str(path).replace("\\", "/")
                for name, path in source_paths.items()
            },
            "source_sha256": {
                name: _file_sha256(path)
                for name, path in source_paths.items()
            },
        },
        "dataset": {
            "runs": list(aggregate["runs"]),
            "n_runs": int(aggregate["n_runs"]),
            "records_per_policy": {
                policy: int(aggregate["policies"][policy]["pooled"]["count"])
                for policy in policies
            },
        },
        "aggregate": {
            policy: _aggregate_policy(aggregate["policies"][policy])
            for policy in policies
        },
        "budget_curve": {
            policy: _budget_policy(budget["policies"][policy])
            for policy in policies
        },
        "exactness_gap": {
            policy: _exactness_policy(exactness["policies"][policy])
            for policy in policies
        },
        "quality_adjusted": {
            policy: _quality_policy(quality["policies"][policy])
            for policy in policies
        },
        "semantic_drift": {
            policy: _semantic_policy(semantic["policies"][policy])
            for policy in policies
        },
        "strict_replay": {
            policy: _strict_policy(strict["policies"][policy])
            for policy in policies
        },
        "strict_casebook": {
            "dataset": casebook["dataset"],
            "primary_case_counts": casebook["primary_case_counts"],
            "flag_counts": casebook["flag_counts"],
            "by_policy": casebook["by_policy"],
            "raw_loss_reasons": casebook["raw_loss_reasons"],
        },
        "strict_paired": {
            "policy_a": paired["policy_a"],
            "policy_b": paired["policy_b"],
            "coverage": paired["coverage"],
            "metrics": {
                metric: _paired_metric(row)
                for metric, row in paired["metrics"].items()
            },
            "case_counts": paired["case_counts"],
            "raw_win_loss": paired["raw_win_loss"],
        },
        "trace_taxonomy": {
            policy: _trace_policy(trace["policies"][policy])
            for policy in policies
        },
    }


def format_markdown(snapshot: dict[str, Any]) -> str:
    policies = list(snapshot["aggregate"])
    lines = [
        "# LeanRepair Real Paper v2 Snapshot",
        "",
        f"- Root: `{snapshot['root']}`",
        f"- Runs: `{snapshot['dataset']['n_runs']}`",
        "- Records per policy: "
        + ", ".join(
            f"`{policy}` {count}"
            for policy, count in snapshot["dataset"]["records_per_policy"].items()
        ),
        "",
        "## Raw Aggregate Outcomes",
        "",
        "| Policy | Records | Solved | Solve rate | Exact | Exact rate | Mean solve | Mean exact |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy in policies:
        row = snapshot["aggregate"][policy]
        lines.append(
            f"| `{policy}` | {row['records']} | {row['solved']} | "
            f"{_pct_ci(row['solve_rate'], row['solve_rate_ci95'])} | "
            f"{row['exact']} | {_pct_ci(row['exact_rate'], row['exact_rate_ci95'])} | "
            f"{_pct_pm(row['solve_rate_mean'], row['solve_rate_std'])} | "
            f"{_pct_pm(row['exact_rate_mean'], row['exact_rate_std'])} |"
        )

    lines.extend(
        [
            "",
            "## Repair Budget Curve",
            "",
            "| Policy | Final budget | Final solved | Solve rate | Exact | Exact rate | Avg checks | Marginal solves |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for policy in policies:
        row = snapshot["budget_curve"][policy]
        final = row["final_budget"]
        lines.append(
            f"| `{policy}` | {final['budget']} | {final['solved']} | "
            f"{_pct(final['solve_rate'])} | {final['exact']} | "
            f"{_pct(final['exact_rate'])} | {final['avg_checks_used']:.2f} | "
            f"{_counts(row['marginal_solves'])} |"
        )

    lines.extend(
        [
            "",
            "## Exactness Gap",
            "",
            "| Policy | Records | Solved | Exact | Solved not exact | Solve-exact gap | Exact given solved | Drift given solved | Avg header similarity |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for policy in policies:
        row = snapshot["exactness_gap"][policy]
        lines.append(
            f"| `{policy}` | {row['records']} | {row['solved']} | {row['exact']} | "
            f"{row['solved_not_exact']} | {_pp(row['solve_exact_gap'])} | "
            f"{_pct(row['exact_given_solved'])} | {_pct(row['drift_given_solved'])} | "
            f"{_pct_or_dash(row['avg_header_similarity'])} |"
        )

    lines.extend(
        [
            "",
            "## Quality-Adjusted Outcomes",
            "",
            "| Policy | Records | Raw solved | Exact | Nondegenerate solved | Degenerate solved | Nondegenerate rate | Degenerate given solved |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for policy in policies:
        row = snapshot["quality_adjusted"][policy]
        lines.append(
            f"| `{policy}` | {row['records']} | {row['solved']} | {row['exact']} | "
            f"{row['nondegenerate_solved']} | {row['degenerate_solved']} | "
            f"{_pct_ci(row['nondegenerate_solved_rate'], row['nondegenerate_solved_rate_ci95'])} | "
            f"{_pct(row['degenerate_given_solved'])} |"
        )

    lines.extend(
        [
            "",
            "## Trace Taxonomy",
            "",
            "| Policy | Records | Lean-OK rate | Exact rate | Avg steps | Median solve step | Top terminal failure | Timeouts |",
            "|---|---:|---:|---:|---:|---:|---|---:|",
        ]
    )
    for policy in policies:
        row = snapshot["trace_taxonomy"][policy]
        lines.append(
            f"| `{policy}` | {row['records']} | {_pct(row['lean_ok_rate'])} | "
            f"{_pct(row['exact_rate'])} | {row['avg_steps']:.2f} | "
            f"{_num_or_dash(row['median_solve_step'])} | "
            f"{_failure_label(row['top_terminal_failure'])} | {row['timeout_records']} |"
        )

    lines.extend(
        [
            "",
            "## Corruption Highlights",
            "",
            "| Policy | Corruption | Records | Final solve | Final exact | Exact given solved | Top terminal failure |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for policy in policies:
        corruptions = sorted(snapshot["budget_curve"][policy]["by_corruption_final"])
        for corruption in corruptions:
            budget_row = snapshot["budget_curve"][policy]["by_corruption_final"][corruption]
            exact_row = snapshot["exactness_gap"][policy]["by_corruption"][corruption]
            trace_row = snapshot["trace_taxonomy"][policy]["by_corruption"][corruption]
            lines.append(
                f"| `{policy}` | `{corruption}` | {budget_row['count']} | "
                f"{_pct(budget_row['solve_rate'])} | {_pct(budget_row['exact_rate'])} | "
                f"{_pct(exact_row['exact_given_solved'])} | "
                f"{_failure_label(trace_row['top_terminal_failure'])} |"
            )

    lines.extend(
        [
            "",
            "## Strict Replay",
            "",
            "| Policy | Raw solved | Strict solved | Strict exact | Strict nonexact | Raw-to-strict loss | Strict retention | Strict exact given strict |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for policy in policies:
        row = snapshot["strict_replay"][policy]
        lines.append(
            f"| `{policy}` | {row['raw_solved']} | {row['strict_solved']} | "
            f"{row['strict_exact']} | {row['strict_not_exact']} | "
            f"{row['raw_to_strict_loss']} | {_pct(row['strict_retention_given_raw'])} | "
            f"{_pct(row['strict_exact_given_strict'])} |"
        )

    paired = snapshot["strict_paired"]
    a = paired["policy_a"]
    b = paired["policy_b"]
    lines.extend(
        [
            "",
            "## Strict Paired Comparison",
            "",
            f"- Baseline policy: `{a}`",
            f"- Compared policy: `{b}`",
            f"- Paired records: `{paired['coverage']['paired_records']}`",
            "",
            "| Metric | Baseline successes | Compared successes | Compared-only | Baseline-only | Lift | Sign-test p |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for metric in ("raw_ok", "strict_ok", "strict_exact"):
        row = paired["metrics"][metric]
        lines.append(
            f"| `{metric}` | {row['policy_a_successes']} | "
            f"{row['policy_b_successes']} | {row['policy_b_only']} | "
            f"{row['policy_a_only']} | {_pp(row['policy_b_lift'])} | "
            f"{row['paired_exact_sign_p_two_sided']:.3e} |"
        )

    lines.extend(
        [
            "",
            "## Degenerate Losses",
            "",
            "| Source | Total | Breakdown |",
            "|---|---:|---|",
            f"| strict replay casebook raw-to-strict loss | "
            f"{snapshot['strict_casebook']['flag_counts']['raw_to_strict_loss']} | "
            f"{_counts(snapshot['strict_casebook']['raw_loss_reasons'])} |",
            f"| compared-policy raw wins lost under strict replay | "
            f"{paired['raw_win_loss']['total']} | "
            f"{_rows(paired['raw_win_loss']['by_reason'])} |",
            "",
            "## Sources",
            "",
        ]
    )
    source_hashes = snapshot["provenance"].get("source_sha256", {})
    for name, path in snapshot["provenance"]["sources"].items():
        digest = source_hashes.get(name)
        if digest:
            lines.append(f"- `{name}`: `{path}` (`sha256:{digest}`)")
        else:
            lines.append(f"- `{name}`: `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def _aggregate_policy(row: dict[str, Any]) -> dict[str, Any]:
    pooled = row["pooled"]
    return {
        "records": int(pooled["count"]),
        "solved": int(pooled["solved"]),
        "exact": int(pooled["exact"]),
        "solve_rate": float(pooled["solve_rate"]),
        "solve_rate_ci95": list(pooled["solve_rate_ci95"]),
        "exact_rate": float(pooled["exact_rate"]),
        "exact_rate_ci95": list(pooled["exact_rate_ci95"]),
        "solve_rate_mean": float(row["solve_rate_mean"]),
        "solve_rate_std": float(row["solve_rate_std"]),
        "exact_rate_mean": float(row["exact_rate_mean"]),
        "exact_rate_std": float(row["exact_rate_std"]),
    }


def _budget_policy(row: dict[str, Any]) -> dict[str, Any]:
    budgets = [_budget_point(point) for point in row["budgets"]]
    return {
        "records": int(row["count"]),
        "max_observed_steps": int(row["max_observed_steps"]),
        "budgets": budgets,
        "final_budget": budgets[-1],
        "marginal_solves": _int_mapping(row["marginal_solves"]),
        "by_corruption_final": {
            corruption: _budget_corruption(corruption_row)
            for corruption, corruption_row in row["by_corruption"].items()
        },
    }


def _budget_point(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "budget": int(row["budget"]),
        "count": int(row["count"]),
        "solved": int(row["solved"]),
        "exact": int(row["exact"]),
        "solve_rate": float(row["solve_rate"]),
        "exact_rate": float(row["exact_rate"]),
        "avg_checks_used": float(row["avg_checks_used"]),
    }


def _budget_corruption(row: dict[str, Any]) -> dict[str, Any]:
    final = _budget_point(row["budgets"][-1])
    final["count"] = int(row["count"])
    return final


def _exactness_policy(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": int(row["count"]),
        "solved": int(row["solved"]),
        "exact": int(row["exact"]),
        "solved_not_exact": int(row["solved_not_exact"]),
        "solve_rate": float(row["solve_rate"]),
        "exact_rate": float(row["exact_rate"]),
        "solve_exact_gap": float(row["solve_rate"]) - float(row["exact_rate"]),
        "exact_given_solved": float(row["exact_given_solved"]),
        "drift_given_solved": float(row["drift_given_solved"]),
        "avg_header_similarity": _optional_float(row.get("avg_header_similarity")),
        "avg_token_jaccard": _optional_float(row.get("avg_token_jaccard")),
        "by_corruption": {
            corruption: _exactness_corruption(corruption_row)
            for corruption, corruption_row in row["by_corruption"].items()
        },
    }


def _exactness_corruption(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": int(row["count"]),
        "solved": int(row["solved"]),
        "exact": int(row["exact"]),
        "solved_not_exact": int(row["solved_not_exact"]),
        "solve_rate": float(row["solve_rate"]),
        "exact_rate": float(row["exact_rate"]),
        "exact_given_solved": float(row["exact_given_solved"]),
        "drift_given_solved": float(row["drift_given_solved"]),
        "avg_header_similarity": _optional_float(row.get("avg_header_similarity")),
        "avg_token_jaccard": _optional_float(row.get("avg_token_jaccard")),
    }


def _quality_policy(row: dict[str, Any]) -> dict[str, Any]:
    pooled = row["pooled"]
    return {
        "records": int(pooled["count"]),
        "solved": int(pooled["solved"]),
        "exact": int(pooled["exact"]),
        "nondegenerate_solved": int(pooled["nondegenerate_solved"]),
        "degenerate_solved": int(pooled["degenerate_solved"]),
        "nondegenerate_solved_rate": float(pooled["nondegenerate_solved_rate"]),
        "nondegenerate_solved_rate_ci95": list(pooled["nondegenerate_solved_rate_ci95"]),
        "degenerate_given_solved": float(pooled["degenerate_given_solved"]),
    }


def _semantic_policy(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": int(row["count"]),
        "solved": int(row["solved"]),
        "exact": int(row["exact"]),
        "degenerate_solved": int(row["degenerate_solved"]),
        "nondegenerate_solved": int(row["nondegenerate_solved"]),
        "degenerate_reasons": dict(row["degenerate_reasons"]),
        "degenerate_given_solved": float(row["degenerate_given_solved"]),
    }


def _strict_policy(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": int(row["count"]),
        "raw_solved": int(row["raw_solved"]),
        "strict_solved": int(row["strict_solved"]),
        "raw_exact": int(row["raw_exact"]),
        "strict_exact": int(row["strict_exact"]),
        "strict_not_exact": int(row["strict_not_exact"]),
        "raw_degenerate_solved": int(row["raw_degenerate_solved"]),
        "raw_to_strict_loss": int(row["raw_to_strict_loss"]),
        "strict_retention_given_raw": float(row["strict_retention_given_raw"]),
        "strict_exact_given_strict": float(row["strict_exact_given_strict"]),
        "raw_degenerate_reasons": dict(row["raw_degenerate_reasons"]),
    }


def _paired_metric(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy_a_successes": int(row["policy_a_successes"]),
        "policy_b_successes": int(row["policy_b_successes"]),
        "policy_a_only": int(row["policy_a_only"]),
        "policy_b_only": int(row["policy_b_only"]),
        "policy_b_lift": float(row["policy_b_lift"]),
        "paired_exact_sign_p_two_sided": float(row["paired_exact_sign_p_two_sided"]),
    }


def _trace_policy(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": int(row["count"]),
        "records_with_trace": int(row["records_with_trace"]),
        "solved": int(row["solved"]),
        "exact": int(row["exact"]),
        "lean_ok_records": int(row["lean_ok_records"]),
        "rejected_lean_ok_records": int(row["rejected_lean_ok_records"]),
        "accepted_after_rejection": int(row["accepted_after_rejection"]),
        "solve_rate": float(row["solve_rate"]),
        "exact_rate": float(row["exact_rate"]),
        "lean_ok_rate": float(row["lean_ok_rate"]),
        "rejected_lean_ok_rate": float(row["rejected_lean_ok_rate"]),
        "avg_steps": float(row["avg_steps"]),
        "median_steps": _optional_float(row.get("median_steps")),
        "median_solve_step": _optional_float(row.get("median_solve_step")),
        "timeout_records": int(row["timeout_records"]),
        "first_error_kind": _int_mapping(row["first_error_kind"]),
        "terminal_error_kind": _int_mapping(row["terminal_error_kind"]),
        "failure_transitions": _int_mapping(row["failure_transitions"]),
        "solved_by_step": _int_mapping(row["solved_by_step"]),
        "top_terminal_failure": _top_terminal_failure(row["terminal_error_kind"]),
        "by_corruption": {
            corruption: _trace_corruption(corruption_row)
            for corruption, corruption_row in row["by_corruption"].items()
        },
    }


def _trace_corruption(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": int(row["count"]),
        "solved": int(row["solved"]),
        "exact": int(row["exact"]),
        "lean_ok_records": int(row["lean_ok_records"]),
        "rejected_lean_ok_records": int(row["rejected_lean_ok_records"]),
        "accepted_after_rejection": int(row["accepted_after_rejection"]),
        "solve_rate": float(row["solve_rate"]),
        "exact_rate": float(row["exact_rate"]),
        "lean_ok_rate": float(row["lean_ok_rate"]),
        "rejected_lean_ok_rate": float(row["rejected_lean_ok_rate"]),
        "avg_steps": float(row["avg_steps"]),
        "first_error_kind": _int_mapping(row["first_error_kind"]),
        "terminal_error_kind": _int_mapping(row["terminal_error_kind"]),
        "failure_transitions": _int_mapping(row["failure_transitions"]),
        "top_terminal_failure": _top_terminal_failure(row["terminal_error_kind"]),
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _int_mapping(mapping: dict[str, Any]) -> dict[str, int]:
    return {str(name): int(count) for name, count in mapping.items()}


def _top_terminal_failure(mapping: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [
        (str(name), int(count))
        for name, count in mapping.items()
        if str(name) != "solved" and int(count) > 0
    ]
    if not candidates:
        return None
    name, count = max(candidates, key=lambda item: item[1])
    return {"kind": name, "count": count}


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _pp(value: float) -> str:
    return f"{100.0 * float(value):+.1f} pp"


def _pct_ci(value: float, ci: list[float]) -> str:
    return f"{_pct(value)} [{100.0 * ci[0]:.1f}, {100.0 * ci[1]:.1f}]"


def _pct_pm(value: float, spread: float) -> str:
    return f"{100.0 * value:.1f}% +/- {100.0 * spread:.1f}%"


def _pct_or_dash(value: float | None) -> str:
    return "-" if value is None else _pct(value)


def _num_or_dash(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}"


def _failure_label(value: dict[str, Any] | None) -> str:
    if not value:
        return "-"
    return f"`{value['kind']}` {value['count']}"


def _counts(counts: dict[str, int]) -> str:
    return ", ".join(f"`{name}` {count}" for name, count in sorted(counts.items()))


def _rows(rows: list[dict[str, Any]]) -> str:
    return ", ".join(f"`{row['name']}` {row['count']}" for row in rows)


def _stale_outputs(expected: dict[Path, str]) -> list[Path]:
    stale = []
    for path, expected_text in expected.items():
        if not path.exists() or path.read_text(encoding="utf-8") != expected_text:
            stale.append(path)
    return stale


def _display_paths(paths: list[Path]) -> str:
    return ", ".join(str(path).replace("\\", "/") for path in paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="results/real_paper_v2")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if generated snapshot outputs differ from the checked-in files",
    )
    args = parser.parse_args()

    root = Path(args.root)
    snapshot = build_snapshot(root)
    json_text = json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n"
    markdown = format_markdown(snapshot)
    output_json = Path(args.output_json) if args.output_json else root / "snapshot_summary.json"
    output_md = Path(args.output_md) if args.output_md else root / "snapshot_summary.md"
    expected = {output_json: json_text, output_md: markdown}

    if args.check:
        stale = _stale_outputs(expected)
        if stale:
            raise SystemExit(
                "Stale snapshot outputs: "
                + _display_paths(stale)
                + "; rerun scripts/summarize_real_paper_snapshot.py without --check"
            )
        print(f"Snapshot outputs are up to date: {_display_paths(list(expected))}")
        return

    output_json.write_text(json_text, encoding="utf-8")
    output_md.write_text(markdown, encoding="utf-8")
    print(f"Wrote {output_json} and {output_md}")


if __name__ == "__main__":
    main()
