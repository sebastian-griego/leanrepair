from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def analyze_records(
    records: list[dict[str, Any]],
    *,
    max_examples: int = 20,
) -> dict[str, Any]:
    first_kinds: Counter[str] = Counter()
    terminal_kinds: Counter[str] = Counter()
    failure_transitions: Counter[str] = Counter()
    solved_by_step: Counter[str] = Counter()
    by_corruption: dict[str, _Bucket] = {}
    failure_examples: list[dict[str, Any]] = []
    step_values: list[int] = []
    elapsed_values: list[float] = []
    solve_steps: list[int] = []
    solved = 0
    exact = 0
    timeout_records = 0
    records_with_trace = 0

    for row in records:
        trace = row.get("trace")
        if not isinstance(trace, list):
            trace = []
        if trace:
            records_with_trace += 1

        corruption = str(row.get("corruption", "unknown") or "unknown")
        ok = bool(row.get("ok", False))
        is_exact = bool(row.get("exact", False))
        steps = _int_value(row.get("steps"), default=len(trace))
        elapsed_ms = _float_value(row.get("elapsed_ms"), default=_trace_elapsed(trace))
        first_kind = _primary_kind(trace[0]) if trace else "no_trace"
        terminal_kind = "solved" if ok else (_terminal_kind(trace) if trace else "no_trace")

        first_kinds[first_kind] += 1
        terminal_kinds[terminal_kind] += 1
        step_values.append(steps)
        elapsed_values.append(elapsed_ms)
        solved += int(ok)
        exact += int(is_exact)
        timeout_records += int(_trace_timed_out(trace))

        if ok:
            solve_step = _first_ok_step(trace) or steps
            solve_steps.append(solve_step)
            solved_by_step[str(solve_step)] += 1
        else:
            transition = f"{first_kind}->{terminal_kind}"
            failure_transitions[transition] += 1
            if len(failure_examples) < max(0, int(max_examples)):
                failure_examples.append(_failure_example(row, first_kind, terminal_kind))

        bucket = by_corruption.setdefault(corruption, _Bucket())
        bucket.add(
            ok=ok,
            exact=is_exact,
            first_kind=first_kind,
            terminal_kind=terminal_kind,
            failure_transition=None if ok else f"{first_kind}->{terminal_kind}",
            steps=steps,
            elapsed_ms=elapsed_ms,
        )

    total = len(records)
    return {
        "count": total,
        "records_with_trace": records_with_trace,
        "solved": solved,
        "exact": exact,
        "solve_rate": _rate(solved, total),
        "exact_rate": _rate(exact, total),
        "avg_steps": mean(step_values) if step_values else 0.0,
        "median_steps": median(step_values) if step_values else 0.0,
        "median_solve_step": median(solve_steps) if solve_steps else None,
        "avg_elapsed_ms": mean(elapsed_values) if elapsed_values else 0.0,
        "timeout_records": timeout_records,
        "first_error_kind": _sorted_counter(first_kinds),
        "terminal_error_kind": _sorted_counter(terminal_kinds),
        "failure_transitions": _sorted_counter(failure_transitions),
        "solved_by_step": _sorted_counter(solved_by_step),
        "by_corruption": {
            name: bucket.to_json_dict()
            for name, bucket in sorted(by_corruption.items(), key=lambda item: item[0])
        },
        "failure_examples": failure_examples,
    }


def analyze_run_dir(
    run_dir: Path,
    policies: Iterable[str],
    *,
    max_examples: int = 20,
) -> dict[str, Any]:
    policy_summaries: dict[str, Any] = {}
    missing: list[str] = []
    for policy in policies:
        path = run_dir / f"{policy}.jsonl"
        if not path.exists():
            missing.append(str(policy))
            continue
        policy_summaries[str(policy)] = analyze_records(
            load_jsonl(path), max_examples=max_examples
        )
    if not policy_summaries:
        raise ValueError(f"no policy JSONL files found under {run_dir}")
    return {
        "root": str(run_dir),
        "runs": {
            run_dir.name: {
                "policies": policy_summaries,
                "missing_policies": missing,
            }
        },
        "policies": policy_summaries,
        "missing_policies": missing,
    }


def analyze_root(
    root: Path,
    policies: Iterable[str],
    *,
    max_examples: int = 20,
) -> dict[str, Any]:
    policies = [str(policy) for policy in policies]
    direct_policy_files = [root / f"{policy}.jsonl" for policy in policies]
    if any(path.exists() for path in direct_policy_files):
        return analyze_run_dir(root, policies, max_examples=max_examples)

    run_dirs = sorted(path for path in root.iterdir() if path.is_dir() and path.name.startswith("run_"))
    if not run_dirs:
        raise ValueError(f"no run_* directories or policy JSONL files found under {root}")

    runs: dict[str, Any] = {}
    aggregate_records: dict[str, list[dict[str, Any]]] = {policy: [] for policy in policies}
    aggregate_missing: Counter[str] = Counter()

    for run_dir in run_dirs:
        run_policies: dict[str, Any] = {}
        run_missing: list[str] = []
        for policy in policies:
            path = run_dir / f"{policy}.jsonl"
            if not path.exists():
                run_missing.append(policy)
                aggregate_missing[policy] += 1
                continue
            rows = load_jsonl(path)
            aggregate_records[policy].extend(rows)
            run_policies[policy] = analyze_records(rows, max_examples=max_examples)
        runs[run_dir.name] = {
            "policies": run_policies,
            "missing_policies": run_missing,
        }

    aggregate = {
        policy: analyze_records(rows, max_examples=max_examples)
        for policy, rows in aggregate_records.items()
        if rows
    }
    if not aggregate:
        raise ValueError(f"no policy JSONL records found under {root}")

    return {
        "root": str(root),
        "runs": runs,
        "policies": aggregate,
        "missing_policy_run_counts": dict(sorted(aggregate_missing.items())),
    }


def format_markdown(summary: dict[str, Any]) -> str:
    policies = summary.get("policies", {})
    lines = [
        "# LeanRepair Trace Taxonomy",
        "",
        f"- Root: `{summary.get('root', '')}`",
        f"- Policies: `{', '.join(sorted(policies))}`",
        "",
        "## Aggregate",
        "",
        "| Policy | Records | Solve Rate | Exact Rate | Avg Steps | Median Solve Step | Timeouts |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, row in sorted(policies.items()):
        median_solve = row["median_solve_step"]
        median_solve_text = "-" if median_solve is None else f"{float(median_solve):.1f}"
        lines.append(
            f"| {policy} | {row['count']} | {_pct(row['solve_rate'])} | "
            f"{_pct(row['exact_rate'])} | {row['avg_steps']:.2f} | "
            f"{median_solve_text} | {row['timeout_records']} |"
        )

    lines.extend(["", "## Terminal Outcomes", ""])
    for policy, row in sorted(policies.items()):
        lines.extend([f"### {policy}", "", "| Terminal kind | Count |", "|---|---:|"])
        for kind, count in _top_items(row.get("terminal_error_kind", {}), limit=12):
            lines.append(f"| {_md(kind)} | {count} |")
        lines.append("")

    lines.extend(["## Failure Transitions", ""])
    for policy, row in sorted(policies.items()):
        lines.extend([f"### {policy}", "", "| First -> terminal | Count |", "|---|---:|"])
        transitions = row.get("failure_transitions", {})
        if transitions:
            for transition, count in _top_items(transitions, limit=12):
                lines.append(f"| {_md(transition)} | {count} |")
        else:
            lines.append("| - | 0 |")
        lines.append("")

    lines.extend(["## By Corruption", ""])
    for policy, row in sorted(policies.items()):
        lines.extend(
            [
                f"### {policy}",
                "",
                "| Corruption | N | Solve Rate | Exact Rate | Top terminal failure |",
                "|---|---:|---:|---:|---|",
            ]
        )
        for corruption, bucket in row.get("by_corruption", {}).items():
            top_terminal = _top_terminal_failure(bucket.get("terminal_error_kind", {}))
            lines.append(
                f"| {_md(corruption)} | {bucket['count']} | {_pct(bucket['solve_rate'])} | "
                f"{_pct(bucket['exact_rate'])} | {_md(top_terminal)} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


class _Bucket:
    def __init__(self) -> None:
        self.count = 0
        self.solved = 0
        self.exact = 0
        self.steps: list[int] = []
        self.elapsed_ms: list[float] = []
        self.first_kinds: Counter[str] = Counter()
        self.terminal_kinds: Counter[str] = Counter()
        self.failure_transitions: Counter[str] = Counter()

    def add(
        self,
        *,
        ok: bool,
        exact: bool,
        first_kind: str,
        terminal_kind: str,
        failure_transition: str | None,
        steps: int,
        elapsed_ms: float,
    ) -> None:
        self.count += 1
        self.solved += int(ok)
        self.exact += int(exact)
        self.steps.append(int(steps))
        self.elapsed_ms.append(float(elapsed_ms))
        self.first_kinds[first_kind] += 1
        self.terminal_kinds[terminal_kind] += 1
        if failure_transition:
            self.failure_transitions[failure_transition] += 1

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "solved": self.solved,
            "exact": self.exact,
            "solve_rate": _rate(self.solved, self.count),
            "exact_rate": _rate(self.exact, self.count),
            "avg_steps": mean(self.steps) if self.steps else 0.0,
            "avg_elapsed_ms": mean(self.elapsed_ms) if self.elapsed_ms else 0.0,
            "first_error_kind": _sorted_counter(self.first_kinds),
            "terminal_error_kind": _sorted_counter(self.terminal_kinds),
            "failure_transitions": _sorted_counter(self.failure_transitions),
        }


def _primary_kind(step: dict[str, Any]) -> str:
    if bool(step.get("ok", False)):
        return "solved"
    if bool(step.get("timed_out", False)):
        return "timeout"
    errors = step.get("errors", [])
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict):
            return str(first.get("kind", "other") or "other")
    return "no_error"


def _terminal_kind(trace: list[dict[str, Any]]) -> str:
    if not trace:
        return "no_trace"
    return _primary_kind(trace[-1])


def _first_ok_step(trace: list[dict[str, Any]]) -> int | None:
    for index, step in enumerate(trace, start=1):
        if bool(step.get("ok", False)):
            return index
    return None


def _trace_timed_out(trace: list[dict[str, Any]]) -> bool:
    return any(bool(step.get("timed_out", False)) for step in trace)


def _trace_elapsed(trace: list[dict[str, Any]]) -> float:
    total = 0.0
    for step in trace:
        total += _float_value(step.get("elapsed_ms"), default=0.0)
    return total


def _failure_example(row: dict[str, Any], first_kind: str, terminal_kind: str) -> dict[str, Any]:
    trace = row.get("trace")
    if not isinstance(trace, list):
        trace = []
    last = trace[-1] if trace else {}
    return {
        "id": row.get("id"),
        "corruption": row.get("corruption", "unknown"),
        "steps": row.get("steps", len(trace)),
        "first_error_kind": first_kind,
        "terminal_error_kind": terminal_kind,
        "candidate0": row.get("candidate0", ""),
        "final": row.get("final", ""),
        "terminal_errors": _error_messages(last),
    }


def _error_messages(step: dict[str, Any]) -> list[str]:
    errors = step.get("errors", [])
    if not isinstance(errors, list):
        return []
    out: list[str] = []
    for err in errors[:3]:
        if isinstance(err, dict):
            out.append(str(err.get("message", "")))
    return out


def _sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    }


def _top_items(mapping: dict[str, int], *, limit: int) -> list[tuple[str, int]]:
    return [(str(key), int(value)) for key, value in list(mapping.items())[: max(0, int(limit))]]


def _top_terminal_failure(mapping: dict[str, int]) -> str:
    for kind, count in mapping.items():
        if kind != "solved":
            return f"{kind} ({count})"
    return "-"


def _rate(numer: int, denom: int) -> float:
    return (float(numer) / float(denom)) if denom else 0.0


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _int_value(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _float_value(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _md(value: object) -> str:
    return str(value).replace("|", "\\|")


__all__ = [
    "analyze_records",
    "analyze_root",
    "analyze_run_dir",
    "format_markdown",
    "load_jsonl",
]
