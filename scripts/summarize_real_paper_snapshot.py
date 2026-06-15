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
    _validate_snapshot_sources(loaded)
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


def _validate_snapshot_sources(loaded: dict[str, dict[str, Any]]) -> None:
    aggregate = loaded["aggregate"]
    policies = set(aggregate["policies"])
    _require_equal("aggregate.n_runs", int(aggregate["n_runs"]), len(aggregate["runs"]))
    aggregate_run_names = _validate_aggregate_runs(aggregate)
    for artifact in (
        "budget_curve",
        "exactness_gap",
        "quality",
        "semantic_drift",
        "strict_replay",
        "trace_taxonomy",
    ):
        _validate_artifact_runs(artifact, loaded[artifact], aggregate, aggregate_run_names)
        artifact_policies = set(loaded[artifact]["policies"])
        if artifact_policies != policies:
            raise ValueError(
                f"Inconsistent source artifact {artifact}.policies: "
                f"{sorted(artifact_policies)} != {sorted(policies)}"
            )

    for policy in sorted(policies):
        records = int(aggregate["policies"][policy]["pooled"]["count"])
        _validate_aggregate_policy(policy, aggregate["policies"][policy])
        _validate_budget_policy(policy, loaded["budget_curve"]["policies"][policy])
        _validate_exactness_policy(policy, loaded["exactness_gap"]["policies"][policy])
        _validate_quality_policy(policy, loaded["quality"]["policies"][policy])
        _validate_semantic_policy(policy, loaded["semantic_drift"]["policies"][policy])
        _validate_strict_policy(policy, loaded["strict_replay"]["policies"][policy])
        _validate_trace_policy(policy, loaded["trace_taxonomy"]["policies"][policy])
        _require_equal(
            f"budget_curve.{policy}.count",
            int(loaded["budget_curve"]["policies"][policy]["count"]),
            records,
        )
        _require_equal(
            f"exactness_gap.{policy}.count",
            int(loaded["exactness_gap"]["policies"][policy]["count"]),
            records,
        )
        _require_equal(
            f"quality.{policy}.pooled.count",
            int(loaded["quality"]["policies"][policy]["pooled"]["count"]),
            records,
        )
        _require_equal(
            f"semantic_drift.{policy}.count",
            int(loaded["semantic_drift"]["policies"][policy]["count"]),
            records,
        )
        _require_equal(
            f"strict_replay.{policy}.count",
            int(loaded["strict_replay"]["policies"][policy]["count"]),
            records,
        )
        _require_equal(
            f"trace_taxonomy.{policy}.count",
            int(loaded["trace_taxonomy"]["policies"][policy]["count"]),
            records,
        )

    casebook_policies = set(loaded["strict_casebook"]["by_policy"])
    if not casebook_policies.issubset(policies):
        raise ValueError(
            "Inconsistent source artifact strict_casebook.by_policy: "
            f"{sorted(casebook_policies)} is not a subset of {sorted(policies)}"
        )
    _validate_casebook_policy_records(loaded["strict_casebook"], aggregate)
    _validate_casebook(loaded["strict_casebook"])

    paired = loaded["strict_paired"]
    policy_a = paired["policy_a"]
    policy_b = paired["policy_b"]
    for policy in (policy_a, policy_b):
        if policy not in policies:
            raise ValueError(
                f"Inconsistent source artifact strict_paired policy {policy!r} "
                f"not in {sorted(policies)}"
            )
    _require_equal(
        "strict_paired.coverage.policy_a_records",
        int(paired["coverage"]["policy_a_records"]),
        int(aggregate["policies"][policy_a]["pooled"]["count"]),
    )
    _require_equal(
        "strict_paired.coverage.policy_b_records",
        int(paired["coverage"]["policy_b_records"]),
        int(aggregate["policies"][policy_b]["pooled"]["count"]),
    )
    _validate_paired_metrics(paired)


def _validate_aggregate_runs(aggregate: dict[str, Any]) -> set[str]:
    run_names = {Path(str(run)).name for run in aggregate["runs"]}
    per_run = aggregate.get("per_run")
    if isinstance(per_run, dict):
        per_run_names = {str(run) for run in per_run}
        if per_run_names != run_names:
            raise ValueError(
                "Inconsistent source artifact aggregate.per_run: "
                f"{sorted(per_run_names)} != {sorted(run_names)}"
            )
    return run_names


def _validate_artifact_runs(
    artifact: str,
    source: dict[str, Any],
    aggregate: dict[str, Any],
    aggregate_run_names: set[str],
) -> None:
    runs = source.get("runs")
    if not isinstance(runs, dict):
        return

    artifact_run_names = {str(run) for run in runs}
    if artifact_run_names != aggregate_run_names:
        raise ValueError(
            f"Inconsistent source artifact {artifact}.runs: "
            f"{sorted(artifact_run_names)} != {sorted(aggregate_run_names)}"
        )

    policies = set(aggregate["policies"])
    aggregate_per_run = aggregate.get("per_run", {})
    for run_name, run_payload in runs.items():
        run_policies = run_payload.get("policies", {})
        artifact_policies = set(run_policies)
        if artifact_policies != policies:
            raise ValueError(
                f"Inconsistent source artifact {artifact}.runs.{run_name}.policies: "
                f"{sorted(artifact_policies)} != {sorted(policies)}"
            )
        if not isinstance(aggregate_per_run, dict) or run_name not in aggregate_per_run:
            continue
        aggregate_run = aggregate_per_run[run_name]
        for policy in sorted(policies):
            if "count" not in run_policies[policy]:
                continue
            _require_equal(
                f"{artifact}.runs.{run_name}.{policy}.count",
                int(run_policies[policy]["count"]),
                int(aggregate_run[policy]["count"]),
            )


def _validate_casebook_policy_records(
    casebook: dict[str, Any],
    aggregate: dict[str, Any],
) -> None:
    dataset_policies = casebook.get("dataset", {}).get("policies")
    if not isinstance(dataset_policies, dict):
        return

    aggregate_counts = {
        policy: int(row["pooled"]["count"])
        for policy, row in aggregate["policies"].items()
    }
    casebook_counts = {str(policy): int(count) for policy, count in dataset_policies.items()}
    if set(casebook_counts) != set(aggregate_counts):
        raise ValueError(
            "Inconsistent source artifact strict_casebook.dataset.policies: "
            f"{sorted(casebook_counts)} != {sorted(aggregate_counts)}"
        )
    for policy, count in sorted(casebook_counts.items()):
        _require_equal(
            f"strict_casebook.dataset.policies.{policy}",
            count,
            aggregate_counts[policy],
        )


def _validate_aggregate_policy(policy: str, row: dict[str, Any]) -> None:
    pooled = row["pooled"]
    count = int(pooled["count"])
    solved = int(pooled["solved"])
    exact = int(pooled["exact"])
    _require_bounds(f"aggregate.{policy}.solved", solved, count)
    _require_bounds(f"aggregate.{policy}.exact", exact, solved)
    _require_rate(f"aggregate.{policy}.solve_rate", pooled["solve_rate"], solved, count)
    _require_rate(f"aggregate.{policy}.exact_rate", pooled["exact_rate"], exact, count)


def _validate_budget_policy(policy: str, row: dict[str, Any]) -> None:
    count = int(row["count"])
    previous_solved = 0
    previous_exact = 0
    for point in row["budgets"]:
        budget = int(point["budget"])
        solved = int(point["solved"])
        exact = int(point["exact"])
        _require_equal(f"budget_curve.{policy}.budget_{budget}.count", int(point["count"]), count)
        _require_bounds(f"budget_curve.{policy}.budget_{budget}.solved", solved, count)
        _require_bounds(f"budget_curve.{policy}.budget_{budget}.exact", exact, solved)
        if solved < previous_solved:
            raise ValueError(
                f"Inconsistent source artifact budget_curve.{policy}.budget_{budget}.solved: "
                f"{solved} < previous {previous_solved}"
            )
        if exact < previous_exact:
            raise ValueError(
                f"Inconsistent source artifact budget_curve.{policy}.budget_{budget}.exact: "
                f"{exact} < previous {previous_exact}"
            )
        _require_rate(f"budget_curve.{policy}.budget_{budget}.solve_rate", point["solve_rate"], solved, count)
        _require_rate(f"budget_curve.{policy}.budget_{budget}.exact_rate", point["exact_rate"], exact, count)
        _require_equal(
            f"budget_curve.{policy}.marginal_solves.{budget}",
            int(row["marginal_solves"].get(str(budget), 0)),
            solved - previous_solved,
        )
        previous_solved = solved
        previous_exact = exact


def _validate_exactness_policy(policy: str, row: dict[str, Any]) -> None:
    count = int(row["count"])
    solved = int(row["solved"])
    exact = int(row["exact"])
    solved_not_exact = int(row["solved_not_exact"])
    _require_bounds(f"exactness_gap.{policy}.solved", solved, count)
    _require_bounds(f"exactness_gap.{policy}.exact", exact, solved)
    _require_equal(f"exactness_gap.{policy}.solved_not_exact", solved_not_exact, solved - exact)
    _require_rate(f"exactness_gap.{policy}.solve_rate", row["solve_rate"], solved, count)
    _require_rate(f"exactness_gap.{policy}.exact_rate", row["exact_rate"], exact, count)
    _require_rate(f"exactness_gap.{policy}.exact_given_solved", row["exact_given_solved"], exact, solved)
    _require_rate(
        f"exactness_gap.{policy}.drift_given_solved",
        row["drift_given_solved"],
        solved_not_exact,
        solved,
    )


def _validate_quality_policy(policy: str, row: dict[str, Any]) -> None:
    pooled = row["pooled"]
    count = int(pooled["count"])
    solved = int(pooled["solved"])
    exact = int(pooled["exact"])
    nondegenerate = int(pooled["nondegenerate_solved"])
    degenerate = int(pooled["degenerate_solved"])
    _require_bounds(f"quality.{policy}.solved", solved, count)
    _require_bounds(f"quality.{policy}.exact", exact, solved)
    _require_equal(f"quality.{policy}.solved_breakdown", nondegenerate + degenerate, solved)
    _require_rate(
        f"quality.{policy}.nondegenerate_solved_rate",
        pooled["nondegenerate_solved_rate"],
        nondegenerate,
        count,
    )
    _require_rate(
        f"quality.{policy}.degenerate_given_solved",
        pooled["degenerate_given_solved"],
        degenerate,
        solved,
    )


def _validate_semantic_policy(policy: str, row: dict[str, Any]) -> None:
    count = int(row["count"])
    solved = int(row["solved"])
    exact = int(row["exact"])
    degenerate = int(row["degenerate_solved"])
    nondegenerate = int(row["nondegenerate_solved"])
    _require_bounds(f"semantic_drift.{policy}.solved", solved, count)
    _require_bounds(f"semantic_drift.{policy}.exact", exact, solved)
    _require_equal(f"semantic_drift.{policy}.solved_breakdown", degenerate + nondegenerate, solved)
    _require_equal(
        f"semantic_drift.{policy}.degenerate_reasons",
        sum(int(value) for value in row["degenerate_reasons"].values()),
        degenerate,
    )
    _require_rate(
        f"semantic_drift.{policy}.degenerate_given_solved",
        row["degenerate_given_solved"],
        degenerate,
        solved,
    )


def _validate_strict_policy(policy: str, row: dict[str, Any]) -> None:
    count = int(row["count"])
    raw_solved = int(row["raw_solved"])
    strict_solved = int(row["strict_solved"])
    raw_exact = int(row["raw_exact"])
    strict_exact = int(row["strict_exact"])
    strict_not_exact = int(row["strict_not_exact"])
    raw_to_strict_loss = int(row["raw_to_strict_loss"])
    _require_bounds(f"strict_replay.{policy}.raw_solved", raw_solved, count)
    _require_bounds(f"strict_replay.{policy}.strict_solved", strict_solved, raw_solved)
    _require_bounds(f"strict_replay.{policy}.raw_exact", raw_exact, raw_solved)
    _require_bounds(f"strict_replay.{policy}.strict_exact", strict_exact, strict_solved)
    _require_equal(
        f"strict_replay.{policy}.strict_nonexact_breakdown",
        strict_exact + strict_not_exact,
        strict_solved,
    )
    _require_equal(
        f"strict_replay.{policy}.raw_to_strict_loss",
        raw_to_strict_loss,
        raw_solved - strict_solved,
    )
    _require_rate(
        f"strict_replay.{policy}.strict_retention_given_raw",
        row["strict_retention_given_raw"],
        strict_solved,
        raw_solved,
    )
    _require_rate(
        f"strict_replay.{policy}.strict_exact_given_strict",
        row["strict_exact_given_strict"],
        strict_exact,
        strict_solved,
    )


def _validate_trace_policy(policy: str, row: dict[str, Any]) -> None:
    count = int(row["count"])
    solved = int(row["solved"])
    exact = int(row["exact"])
    lean_ok = int(row["lean_ok_records"])
    _require_bounds(f"trace_taxonomy.{policy}.records_with_trace", int(row["records_with_trace"]), count)
    _require_bounds(f"trace_taxonomy.{policy}.solved", solved, count)
    _require_bounds(f"trace_taxonomy.{policy}.exact", exact, solved)
    _require_bounds(f"trace_taxonomy.{policy}.lean_ok_records", lean_ok, count)
    _require_rate(f"trace_taxonomy.{policy}.solve_rate", row["solve_rate"], solved, count)
    _require_rate(f"trace_taxonomy.{policy}.exact_rate", row["exact_rate"], exact, count)
    _require_rate(f"trace_taxonomy.{policy}.lean_ok_rate", row["lean_ok_rate"], lean_ok, count)


def _validate_casebook(casebook: dict[str, Any]) -> None:
    dataset = casebook["dataset"]
    flag_counts = {name: int(count) for name, count in casebook["flag_counts"].items()}
    by_policy = casebook["by_policy"]
    focused_cases = int(dataset["focused_cases"])
    _require_equal("strict_casebook.flag_counts", sum(flag_counts.values()), focused_cases)
    if "policies" in dataset:
        policy_records = {name: int(count) for name, count in dataset["policies"].items()}
        _require_equal(
            "strict_casebook.dataset.policy_records",
            sum(policy_records.values()),
            int(dataset["records"]),
        )
    primary_counts = {name: int(count) for name, count in casebook["primary_case_counts"].items()}
    if "unsolved" in primary_counts:
        _require_equal(
            "strict_casebook.primary_case_counts",
            sum(primary_counts.values()),
            int(dataset["records"]),
        )
    for flag, count in flag_counts.items():
        _require_equal(
            f"strict_casebook.by_policy.{flag}",
            sum(int(row.get(flag, 0)) for row in by_policy.values()),
            count,
        )
    if "raw_to_strict_loss" in flag_counts:
        _require_equal(
            "strict_casebook.raw_loss_reasons",
            sum(int(count) for count in casebook["raw_loss_reasons"].values()),
            flag_counts["raw_to_strict_loss"],
        )


def _validate_paired_metrics(paired: dict[str, Any]) -> None:
    coverage = paired["coverage"]
    paired_records = int(coverage["paired_records"])
    _require_equal(
        "strict_paired.coverage.policy_a_total",
        paired_records + int(coverage["policy_a_unpaired"]),
        int(coverage["policy_a_records"]),
    )
    _require_equal(
        "strict_paired.coverage.policy_b_total",
        paired_records + int(coverage["policy_b_unpaired"]),
        int(coverage["policy_b_records"]),
    )
    for name, row in paired["metrics"].items():
        _validate_paired_metric(f"strict_paired.metrics.{name}", row, paired_records)

    by_policy = paired.get("by_policy", {})
    for policy, expected_records in (
        (paired["policy_a"], int(coverage["policy_a_records"])),
        (paired["policy_b"], int(coverage["policy_b_records"])),
    ):
        if policy not in by_policy:
            continue
        row = by_policy[policy]
        records = int(row["records"])
        raw_ok = int(row["raw_ok"])
        strict_ok = int(row["strict_ok"])
        strict_exact = int(row["strict_exact"])
        raw_loss = int(row["raw_to_strict_loss"])
        _require_equal(f"strict_paired.by_policy.{policy}.records", records, expected_records)
        _require_bounds(f"strict_paired.by_policy.{policy}.raw_ok", raw_ok, records)
        _require_bounds(f"strict_paired.by_policy.{policy}.strict_ok", strict_ok, raw_ok)
        _require_bounds(f"strict_paired.by_policy.{policy}.strict_exact", strict_exact, strict_ok)
        _require_equal(
            f"strict_paired.by_policy.{policy}.raw_to_strict_loss",
            raw_loss,
            raw_ok - strict_ok,
        )
        _require_equal(
            f"strict_paired.by_policy.{policy}.raw_degenerate",
            int(row["raw_degenerate"]),
            raw_loss,
        )
        _require_rate(
            f"strict_paired.by_policy.{policy}.strict_retention",
            row["strict_retention"],
            strict_ok,
            raw_ok,
        )

    raw_win_loss = paired.get("raw_win_loss", {})
    if raw_win_loss:
        total = int(raw_win_loss["total"])
        if "policy_b_raw_wins_lost_by_strict" in paired.get("case_counts", {}):
            _require_equal(
                "strict_paired.case_counts.policy_b_raw_wins_lost_by_strict",
                int(paired["case_counts"]["policy_b_raw_wins_lost_by_strict"]),
                total,
            )
        for label in ("by_reason", "by_corruption", "by_reason_and_corruption"):
            if label in raw_win_loss:
                _validate_count_share_rows(
                    f"strict_paired.raw_win_loss.{label}",
                    raw_win_loss[label],
                    total,
                )


def _validate_paired_metric(label: str, row: dict[str, Any], expected_total: int) -> None:
    total = int(row["n_total"])
    both = int(row["both_success"])
    policy_a_only = int(row["policy_a_only"])
    policy_b_only = int(row["policy_b_only"])
    neither = int(row["neither_success"])
    policy_a_successes = int(row["policy_a_successes"])
    policy_b_successes = int(row["policy_b_successes"])
    _require_equal(f"{label}.n_total", total, expected_total)
    _require_equal(f"{label}.outcome_partition", both + policy_a_only + policy_b_only + neither, total)
    _require_equal(f"{label}.policy_a_successes", both + policy_a_only, policy_a_successes)
    _require_equal(f"{label}.policy_b_successes", both + policy_b_only, policy_b_successes)
    _require_equal(f"{label}.discordant_total", int(row["discordant_total"]), policy_a_only + policy_b_only)
    _require_rate(f"{label}.policy_a_rate", row["policy_a_rate"], policy_a_successes, total)
    _require_rate(f"{label}.policy_b_rate", row["policy_b_rate"], policy_b_successes, total)
    _require_close(
        f"{label}.policy_b_lift",
        float(row["policy_b_lift"]),
        float(row["policy_b_rate"]) - float(row["policy_a_rate"]),
    )
    discordant_total = policy_a_only + policy_b_only
    _require_rate(
        f"{label}.policy_b_win_rate_on_discordant",
        row["policy_b_win_rate_on_discordant"],
        policy_b_only,
        discordant_total,
    )


def _validate_count_share_rows(label: str, rows: list[dict[str, Any]], total: int) -> None:
    _require_equal(label, sum(int(row["count"]) for row in rows), total)
    for row in rows:
        name = str(row.get("name") or row.get("reason") or "row")
        if "corruption" in row:
            name += f".{row['corruption']}"
        _require_rate(f"{label}.{name}.share", row["share"], int(row["count"]), total)


def _require_equal(label: str, actual: int, expected: int) -> None:
    if actual != expected:
        raise ValueError(f"Inconsistent source artifact {label}: {actual} != {expected}")


def _require_bounds(label: str, value: int, total: int) -> None:
    if value < 0 or value > total:
        raise ValueError(f"Inconsistent source artifact {label}: {value} outside [0, {total}]")


def _require_rate(label: str, actual: Any, successes: int, total: int) -> None:
    expected = 0.0 if total == 0 else float(successes) / float(total)
    _require_rate_bounds(label, actual)
    _require_rate_bounds(f"{label}.expected", expected)
    _require_close(label, float(actual), expected)


def _require_rate_bounds(label: str, value: Any) -> None:
    numeric = float(value)
    if numeric < -1e-12 or numeric > 1.0 + 1e-12:
        raise ValueError(
            f"Inconsistent source artifact {label}: {numeric} outside [0, 1]"
        )


def _require_close(label: str, actual: float, expected: float) -> None:
    if abs(float(actual) - expected) > 1e-9:
        raise ValueError(
            f"Inconsistent source artifact {label}: {float(actual)} != {expected}"
        )


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
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def _source_hash_mismatches(
    snapshot: dict[str, Any],
    *,
    base_dir: Path,
) -> list[dict[str, str]]:
    provenance = snapshot.get("provenance", {})
    sources = provenance.get("sources", {})
    expected_hashes = provenance.get("source_sha256", {})
    mismatches = []
    for name, path_text in sources.items():
        expected = expected_hashes.get(name)
        if not expected:
            mismatches.append(
                {
                    "name": str(name),
                    "path": str(path_text),
                    "expected": "<missing from source_sha256>",
                    "actual": "<not checked>",
                }
            )
            continue
        path = _resolve_source_path(str(path_text), base_dir=base_dir)
        if not path.exists():
            mismatches.append(
                {
                    "name": str(name),
                    "path": str(path_text),
                    "expected": expected,
                    "actual": "<missing file>",
                }
            )
            continue
        actual = _file_sha256(path)
        if actual != expected:
            mismatches.append(
                {
                    "name": str(name),
                    "path": str(path_text),
                    "expected": expected,
                    "actual": actual,
                }
            )
    for name in sorted(set(expected_hashes) - set(sources)):
        mismatches.append(
            {
                "name": str(name),
                "path": "<missing from sources>",
                "expected": str(expected_hashes[name]),
                "actual": "<not checked>",
            }
        )
    return mismatches


def _resolve_source_path(path_text: str, *, base_dir: Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else base_dir / path


def _display_paths(paths: list[Path]) -> str:
    return ", ".join(str(path).replace("\\", "/") for path in paths)


def _display_hash_mismatches(mismatches: list[dict[str, str]]) -> str:
    return "; ".join(
        f"{row['name']} {row['path']} expected {row['expected']} got {row['actual']}"
        for row in mismatches
    )


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


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
    parser.add_argument(
        "--verify-source-hashes",
        action="store_true",
        help="validate source_sha256 entries in the snapshot JSON against current source files",
    )
    args = parser.parse_args()

    root = Path(args.root)
    output_json = Path(args.output_json) if args.output_json else root / "snapshot_summary.json"
    if args.verify_source_hashes:
        snapshot = _load_json(output_json)
        mismatches = _source_hash_mismatches(snapshot, base_dir=Path.cwd())
        if mismatches:
            raise SystemExit(
                "Source hash verification failed for "
                + str(output_json).replace("\\", "/")
                + ": "
                + _display_hash_mismatches(mismatches)
            )
        print(f"Source hashes verified for {output_json}")
        return

    snapshot = build_snapshot(root)
    json_text = json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n"
    markdown = format_markdown(snapshot)
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

    _write_text(output_json, json_text)
    _write_text(output_md, markdown)
    print(f"Wrote {output_json} and {output_md}")


if __name__ == "__main__":
    main()
