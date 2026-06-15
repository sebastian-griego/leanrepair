from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from jsonl_io import load_policy_result_objects


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return load_policy_result_objects(path)


def analyze_records(
    records: list[dict[str, Any]],
    *,
    max_budget: int | None = None,
) -> dict[str, Any]:
    if not records:
        return {
            "count": 0,
            "max_observed_steps": 0,
            "budgets": [],
            "marginal_solves": {},
            "by_corruption": {},
        }

    prepared = [_prepare_record(row) for row in records]
    observed_max = max(row["observed_steps"] for row in prepared)
    limit = observed_max if max_budget is None or int(max_budget) <= 0 else int(max_budget)
    limit = max(1, limit)

    budgets = [_budget_row(prepared, budget) for budget in range(1, limit + 1)]
    marginal_solves = _marginal_solves(prepared, limit)

    corruption_buckets: dict[str, list[dict[str, Any]]] = {}
    for row in prepared:
        corruption_buckets.setdefault(row["corruption"], []).append(row)

    return {
        "count": len(prepared),
        "max_observed_steps": int(observed_max),
        "budgets": budgets,
        "marginal_solves": marginal_solves,
        "by_corruption": {
            corruption: {
                "count": len(rows),
                "budgets": [_budget_row(rows, budget) for budget in range(1, limit + 1)],
                "marginal_solves": _marginal_solves(rows, limit),
            }
            for corruption, rows in sorted(corruption_buckets.items())
        },
    }


def analyze_root(
    root: Path,
    policies: Iterable[str],
    *,
    max_budget: int | None = None,
) -> dict[str, Any]:
    policies = [str(policy) for policy in policies]
    direct_policy_files = [root / f"{policy}.jsonl" for policy in policies]
    if any(path.exists() for path in direct_policy_files):
        policy_summaries: dict[str, Any] = {}
        missing: list[str] = []
        for policy, path in zip(policies, direct_policy_files):
            if not path.exists():
                missing.append(policy)
                continue
            policy_summaries[policy] = analyze_records(
                load_jsonl(path), max_budget=max_budget
            )
        if not policy_summaries:
            raise ValueError(f"no policy JSONL files found under {root}")
        return {
            "root": str(root),
            "policies": policy_summaries,
            "missing_policies": missing,
            "runs": {
                root.name: {
                    "policies": policy_summaries,
                    "missing_policies": missing,
                }
            },
        }

    run_dirs = sorted(path for path in root.iterdir() if path.is_dir() and path.name.startswith("run_"))
    if not run_dirs:
        raise ValueError(f"no run_* directories or policy JSONL files found under {root}")

    aggregate_records: dict[str, list[dict[str, Any]]] = {policy: [] for policy in policies}
    missing_policy_run_counts: Counter[str] = Counter()
    runs: dict[str, Any] = {}
    for run_dir in run_dirs:
        run_policies: dict[str, Any] = {}
        missing: list[str] = []
        for policy in policies:
            path = run_dir / f"{policy}.jsonl"
            if not path.exists():
                missing.append(policy)
                missing_policy_run_counts[policy] += 1
                continue
            rows = load_jsonl(path)
            aggregate_records[policy].extend(rows)
            run_policies[policy] = analyze_records(rows, max_budget=max_budget)
        runs[run_dir.name] = {
            "policies": run_policies,
            "missing_policies": missing,
        }

    aggregate = {
        policy: analyze_records(rows, max_budget=max_budget)
        for policy, rows in aggregate_records.items()
        if rows
    }
    if not aggregate:
        raise ValueError(f"no policy JSONL records found under {root}")

    return {
        "root": str(root),
        "policies": aggregate,
        "runs": runs,
        "missing_policy_run_counts": dict(sorted(missing_policy_run_counts.items())),
    }


def format_markdown(summary: dict[str, Any]) -> str:
    policies = summary.get("policies", {})
    lines = [
        "# LeanRepair Repair-Budget Curve",
        "",
        f"- Root: `{summary.get('root', '')}`",
        f"- Policies: `{', '.join(sorted(policies))}`",
        "",
        "## Aggregate Budget Curve",
        "",
        "| Policy | Budget | Solve Rate | Exact Rate | Solved | Exact | Avg Checks Used | Marginal Solves |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, row in sorted(policies.items()):
        marginal = row.get("marginal_solves", {})
        for budget in row.get("budgets", []):
            step = str(budget["budget"])
            lines.append(
                f"| {policy} | {budget['budget']} | {_pct(budget['solve_rate'])} | "
                f"{_pct(budget['exact_rate'])} | {budget['solved']} | {budget['exact']} | "
                f"{budget['avg_checks_used']:.2f} | {marginal.get(step, 0)} |"
            )

    lines.extend(["", "## Final By Corruption", ""])
    for policy, row in sorted(policies.items()):
        lines.extend(
            [
                f"### {policy}",
                "",
                "| Corruption | Final Solve Rate | Final Exact Rate | Final Solved | Final Exact |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for corruption, bucket in row.get("by_corruption", {}).items():
            budgets = bucket.get("budgets", [])
            if not budgets:
                continue
            final = budgets[-1]
            lines.append(
                f"| {_md(corruption)} | {_pct(final['solve_rate'])} | "
                f"{_pct(final['exact_rate'])} | {final['solved']} | {final['exact']} |"
            )
        lines.append("")
    return "\n".join(lines)


def _prepare_record(row: dict[str, Any]) -> dict[str, Any]:
    trace = row.get("trace")
    if not isinstance(trace, list):
        trace = []
    observed_steps = _int_value(row.get("steps"), default=len(trace))
    if observed_steps <= 0:
        observed_steps = len(trace)
    if observed_steps <= 0:
        observed_steps = 1
    first_ok = _first_ok_step(trace)
    if first_ok is None and bool(row.get("ok", False)):
        first_ok = observed_steps
    return {
        "id": str(row.get("id", "")),
        "corruption": str(row.get("corruption", "unknown") or "unknown"),
        "ok": bool(row.get("ok", False)),
        "exact": bool(row.get("exact", False)),
        "observed_steps": int(observed_steps),
        "solve_step": first_ok,
    }


def _budget_row(rows: list[dict[str, Any]], budget: int) -> dict[str, Any]:
    solved = 0
    exact = 0
    checks_used = 0
    for row in rows:
        solve_step = row["solve_step"]
        solved_with_budget = solve_step is not None and int(solve_step) <= int(budget)
        solved += int(solved_with_budget)
        exact += int(solved_with_budget and row["exact"])
        if solved_with_budget:
            checks_used += int(solve_step)
        else:
            checks_used += min(int(row["observed_steps"]), int(budget))
    total = len(rows)
    return {
        "budget": int(budget),
        "count": int(total),
        "solved": int(solved),
        "exact": int(exact),
        "solve_rate": _rate(solved, total),
        "exact_rate": _rate(exact, total),
        "avg_checks_used": checks_used / float(total) if total else 0.0,
    }


def _marginal_solves(rows: list[dict[str, Any]], max_budget: int) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        solve_step = row["solve_step"]
        if solve_step is None:
            continue
        if 1 <= int(solve_step) <= int(max_budget):
            counts[str(int(solve_step))] += 1
    return {str(step): int(counts.get(str(step), 0)) for step in range(1, max_budget + 1)}


def _first_ok_step(trace: list[dict[str, Any]]) -> int | None:
    for index, step in enumerate(trace, start=1):
        if bool(step.get("ok", False)):
            return index
    return None


def _rate(numer: int, denom: int) -> float:
    return (float(numer) / float(denom)) if denom else 0.0


def _int_value(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _md(value: object) -> str:
    return str(value).replace("|", "\\|")


__all__ = ["analyze_records", "analyze_root", "format_markdown", "load_jsonl"]
