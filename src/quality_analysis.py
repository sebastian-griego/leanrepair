from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Iterable

import semantic_drift_analysis as sda


def analyze_root(
    root: Path,
    policies: Iterable[str],
    *,
    token_recall_floor: float = 0.2,
) -> dict[str, Any]:
    policies = [str(policy) for policy in policies]
    direct_policy_files = [root / f"{policy}.jsonl" for policy in policies]
    if any(path.exists() for path in direct_policy_files):
        return _analyze_run_set(
            root,
            [root],
            policies,
            token_recall_floor=token_recall_floor,
        )

    run_dirs = sorted(path for path in root.iterdir() if path.is_dir() and path.name.startswith("run_"))
    if not run_dirs:
        raise ValueError(f"no run_* directories or policy JSONL files found under {root}")
    return _analyze_run_set(
        root,
        run_dirs,
        policies,
        token_recall_floor=token_recall_floor,
    )


def format_markdown(summary: dict[str, Any]) -> str:
    policies = summary.get("policies", {})
    lines = [
        "# LeanRepair Quality-Adjusted Summary",
        "",
        f"- Root: `{summary.get('root', '')}`",
        f"- Runs: `{len(summary.get('runs', {}))}`",
        f"- Token-recall floor: `{summary.get('token_recall_floor', 0.2):.2f}`",
        "",
        "## Pooled Metrics",
        "",
        "| Policy | Records | Solved | Exact | Nondegenerate Solved | Degenerate Solved | Pooled Solve | Pooled Exact | Pooled Nondegenerate | Degenerate Given Solved |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, row in sorted(policies.items()):
        pooled = row["pooled"]
        lines.append(
            f"| {policy} | {pooled['count']} | {pooled['solved']} | {pooled['exact']} | "
            f"{pooled['nondegenerate_solved']} | {pooled['degenerate_solved']} | "
            f"{_pct_ci(pooled['solve_rate'], pooled['solve_rate_ci95'])} | "
            f"{_pct_ci(pooled['exact_rate'], pooled['exact_rate_ci95'])} | "
            f"{_pct_ci(pooled['nondegenerate_solved_rate'], pooled['nondegenerate_solved_rate_ci95'])} | "
            f"{_pct(pooled['degenerate_given_solved'])} |"
        )

    lines.extend(
        [
            "",
            "## Mean Across Runs",
            "",
            "| Policy | Solve Rate | Exact Rate | Nondegenerate Rate | Degenerate Rate |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for policy, row in sorted(policies.items()):
        lines.append(
            f"| {policy} | {_pct_pm(row['solve_rate_mean'], row['solve_rate_std'])} | "
            f"{_pct_pm(row['exact_rate_mean'], row['exact_rate_std'])} | "
            f"{_pct_pm(row['nondegenerate_solved_rate_mean'], row['nondegenerate_solved_rate_std'])} | "
            f"{_pct_pm(row['degenerate_solved_rate_mean'], row['degenerate_solved_rate_std'])} |"
        )

    lines.extend(["", "## Pooled By Corruption", ""])
    for policy, row in sorted(policies.items()):
        lines.extend(
            [
                f"### {policy}",
                "",
                "| Corruption | N | Solved | Exact | Nondegenerate | Degenerate | Nondegenerate Rate |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for corruption, bucket in row["pooled"].get("by_corruption", {}).items():
            lines.append(
                f"| {_md(corruption)} | {bucket['count']} | {bucket['solved']} | "
                f"{bucket['exact']} | {bucket['nondegenerate_solved']} | "
                f"{bucket['degenerate_solved']} | {_pct(bucket['nondegenerate_solved_rate'])} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip()


def _analyze_run_set(
    root: Path,
    run_dirs: list[Path],
    policies: list[str],
    *,
    token_recall_floor: float,
) -> dict[str, Any]:
    runs: dict[str, Any] = {}
    aggregate_rows: dict[str, list[dict[str, Any]]] = {policy: [] for policy in policies}
    missing: Counter[str] = Counter()

    for run_dir in run_dirs:
        run_policies: dict[str, Any] = {}
        for policy in policies:
            path = run_dir / f"{policy}.jsonl"
            if not path.exists():
                missing[policy] += 1
                continue
            rows = sda.load_jsonl(path)
            aggregate_rows[policy].extend(rows)
            run_policies[policy] = _quality_from_semantic(
                sda.analyze_records(rows, token_recall_floor=token_recall_floor)
            )
        runs[run_dir.name] = {"policies": run_policies}

    policy_summaries: dict[str, Any] = {}
    for policy, rows in aggregate_rows.items():
        if not rows:
            continue
        pooled = _quality_from_semantic(
            sda.analyze_records(rows, token_recall_floor=token_recall_floor)
        )
        run_rows = [
            run["policies"][policy]
            for run in runs.values()
            if policy in run["policies"]
        ]
        policy_summaries[policy] = {
            "pooled": pooled,
            "runs": len(run_rows),
            **_mean_std("solve_rate", run_rows),
            **_mean_std("exact_rate", run_rows),
            **_mean_std("nondegenerate_solved_rate", run_rows),
            **_mean_std("degenerate_solved_rate", run_rows),
        }

    if not policy_summaries:
        raise ValueError(f"no policy JSONL records found under {root}")

    return {
        "root": str(root),
        "token_recall_floor": float(token_recall_floor),
        "runs": runs,
        "policies": policy_summaries,
        "missing_policy_run_counts": dict(sorted(missing.items())),
    }


def _quality_from_semantic(summary: dict[str, Any]) -> dict[str, Any]:
    count = int(summary["count"])
    solved = int(summary["solved"])
    exact = int(summary["exact"])
    degenerate = int(summary["degenerate_solved"])
    nondegenerate = int(summary["nondegenerate_solved"])
    solve_ci = _wilson_interval(solved, count)
    exact_ci = _wilson_interval(exact, count)
    nondegenerate_ci = _wilson_interval(nondegenerate, count)
    degenerate_ci = _wilson_interval(degenerate, count)
    return {
        "count": count,
        "solved": solved,
        "exact": exact,
        "degenerate_solved": degenerate,
        "nondegenerate_solved": nondegenerate,
        "solve_rate": _rate(solved, count),
        "solve_rate_ci95": list(solve_ci),
        "exact_rate": _rate(exact, count),
        "exact_rate_ci95": list(exact_ci),
        "degenerate_solved_rate": _rate(degenerate, count),
        "degenerate_solved_rate_ci95": list(degenerate_ci),
        "nondegenerate_solved_rate": _rate(nondegenerate, count),
        "nondegenerate_solved_rate_ci95": list(nondegenerate_ci),
        "degenerate_given_solved": _rate(degenerate, solved),
        "avg_target_token_recall": summary["avg_target_token_recall"],
        "avg_binder_retention": summary["avg_binder_retention"],
        "degenerate_reasons": summary["degenerate_reasons"],
        "by_corruption": {
            name: _quality_from_semantic_bucket(bucket)
            for name, bucket in summary.get("by_corruption", {}).items()
        },
    }


def _quality_from_semantic_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    count = int(bucket["count"])
    solved = int(bucket["solved"])
    exact = int(bucket["exact"])
    degenerate = int(bucket["degenerate_solved"])
    nondegenerate = int(bucket["nondegenerate_solved"])
    return {
        "count": count,
        "solved": solved,
        "exact": exact,
        "degenerate_solved": degenerate,
        "nondegenerate_solved": nondegenerate,
        "solve_rate": _rate(solved, count),
        "exact_rate": _rate(exact, count),
        "degenerate_solved_rate": _rate(degenerate, count),
        "nondegenerate_solved_rate": _rate(nondegenerate, count),
        "degenerate_given_solved": _rate(degenerate, solved),
    }


def _mean_std(key: str, rows: list[dict[str, Any]]) -> dict[str, float]:
    values = [float(row[key]) for row in rows]
    if not values:
        return {f"{key}_mean": 0.0, f"{key}_std": 0.0}
    return {
        f"{key}_mean": mean(values),
        f"{key}_std": stdev(values) if len(values) > 1 else 0.0,
    }


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    spread = z * ((p * (1.0 - p) + z * z / (4.0 * total)) / total) ** 0.5
    lo = (centre - spread) / denom
    hi = (centre + spread) / denom
    return max(0.0, lo), min(1.0, hi)


def _rate(numer: int, denom: int) -> float:
    return (float(numer) / float(denom)) if denom else 0.0


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _pct_ci(value: float, ci: list[float]) -> str:
    return f"{_pct(value)} [{100.0 * ci[0]:.1f}, {100.0 * ci[1]:.1f}]"


def _pct_pm(mean_value: float, std_value: float) -> str:
    return f"{100.0 * float(mean_value):.1f}% +/- {100.0 * float(std_value):.1f}%"


def _md(value: object) -> str:
    return str(value).replace("|", "\\|")


__all__ = ["analyze_root", "format_markdown"]
