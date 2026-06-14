from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable

import semantic_drift_analysis as sda


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
    token_recall_floor: float = 0.2,
    max_examples: int = 20,
) -> dict[str, Any]:
    replays = replay_records(records, token_recall_floor=token_recall_floor)
    return _summarize_replays(replays, max_examples=max_examples)


def replay_records(
    records: Iterable[dict[str, Any]],
    *,
    token_recall_floor: float = 0.2,
) -> list[dict[str, Any]]:
    return [
        replay_record(row, token_recall_floor=token_recall_floor)
        for row in records
    ]


def replay_record(
    row: dict[str, Any],
    *,
    token_recall_floor: float = 0.2,
) -> dict[str, Any]:
    raw_candidates = _accepted_trace_candidates(
        row,
        token_recall_floor=token_recall_floor,
    )
    fallback = sda.classify_record(row, token_recall_floor=token_recall_floor)
    if not raw_candidates and fallback["ok"]:
        fallback = dict(fallback)
        fallback["step_index"] = None
        raw_candidates = [fallback]

    raw = raw_candidates[0] if raw_candidates else _empty_candidate(row)
    strict = next(
        (candidate for candidate in raw_candidates if not candidate["degenerate"]),
        None,
    )
    discarded_degenerate_steps = sum(
        1
        for candidate in raw_candidates
        if candidate["degenerate"] and _before_strict(candidate, strict)
    )
    recovered_after_degenerate = bool(
        raw_candidates
        and raw_candidates[0]["degenerate"]
        and strict is not None
        and _step_order(strict) > _step_order(raw_candidates[0])
    )

    return {
        "id": str(row.get("id", "")),
        "policy": str(row.get("policy", "")),
        "corruption": str(row.get("corruption", "unknown") or "unknown"),
        "reported_ok": bool(row.get("ok", False)),
        "raw_ok": bool(raw["ok"]),
        "raw_exact": bool(raw["exact"]),
        "raw_degenerate": bool(raw["degenerate"]),
        "raw_reason": str(raw.get("reason", "")),
        "raw_step_index": raw.get("step_index"),
        "raw_final_header": str(raw.get("final_header", "")),
        "raw_final_goal": str(raw.get("final_goal", "")),
        "target_header": str(raw.get("target_header", "")),
        "target_goal": str(raw.get("target_goal", "")),
        "strict_ok": strict is not None,
        "strict_exact": bool(strict and strict["exact"]),
        "strict_step_index": strict.get("step_index") if strict else None,
        "strict_final_header": str(strict.get("final_header", "")) if strict else "",
        "strict_final_goal": str(strict.get("final_goal", "")) if strict else "",
        "discarded_degenerate_ok_steps": int(discarded_degenerate_steps),
        "recovered_after_degenerate": recovered_after_degenerate,
        "changed_accepted_output": bool(
            strict is not None and raw["final_header"] != strict["final_header"]
        ),
    }


def analyze_run_dir(
    run_dir: Path,
    policies: Iterable[str],
    *,
    token_recall_floor: float = 0.2,
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
            load_jsonl(path),
            token_recall_floor=token_recall_floor,
            max_examples=max_examples,
        )
    if not policy_summaries:
        raise ValueError(f"no policy JSONL files found under {run_dir}")
    return {
        "root": str(run_dir),
        "token_recall_floor": float(token_recall_floor),
        "runs": {
            run_dir.name: {
                "policies": policy_summaries,
                "missing_policies": missing,
            }
        },
        "policies": policy_summaries,
        "missing_policies": missing,
    }


def replay_run_dir(
    run_dir: Path,
    policies: Iterable[str],
    *,
    token_recall_floor: float = 0.2,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for policy in policies:
        path = run_dir / f"{policy}.jsonl"
        if not path.exists():
            continue
        for row in load_jsonl(path):
            replay = replay_record(row, token_recall_floor=token_recall_floor)
            replay["run"] = run_dir.name
            if not replay["policy"]:
                replay["policy"] = str(policy)
            rows.append(replay)
    return rows


def analyze_root(
    root: Path,
    policies: Iterable[str],
    *,
    token_recall_floor: float = 0.2,
    max_examples: int = 20,
) -> dict[str, Any]:
    policies = [str(policy) for policy in policies]
    direct_policy_files = [root / f"{policy}.jsonl" for policy in policies]
    if any(path.exists() for path in direct_policy_files):
        return analyze_run_dir(
            root,
            policies,
            token_recall_floor=token_recall_floor,
            max_examples=max_examples,
        )

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
            run_policies[policy] = analyze_records(
                rows,
                token_recall_floor=token_recall_floor,
                max_examples=max_examples,
            )
        runs[run_dir.name] = {
            "policies": run_policies,
            "missing_policies": run_missing,
        }

    aggregate = {
        policy: analyze_records(
            rows,
            token_recall_floor=token_recall_floor,
            max_examples=max_examples,
        )
        for policy, rows in aggregate_records.items()
        if rows
    }
    if not aggregate:
        raise ValueError(f"no policy JSONL records found under {root}")

    return {
        "root": str(root),
        "token_recall_floor": float(token_recall_floor),
        "runs": runs,
        "policies": aggregate,
        "missing_policy_run_counts": dict(sorted(aggregate_missing.items())),
    }


def replay_root(
    root: Path,
    policies: Iterable[str],
    *,
    token_recall_floor: float = 0.2,
) -> list[dict[str, Any]]:
    policies = [str(policy) for policy in policies]
    direct_policy_files = [root / f"{policy}.jsonl" for policy in policies]
    if any(path.exists() for path in direct_policy_files):
        return replay_run_dir(
            root,
            policies,
            token_recall_floor=token_recall_floor,
        )

    run_dirs = sorted(path for path in root.iterdir() if path.is_dir() and path.name.startswith("run_"))
    if not run_dirs:
        raise ValueError(f"no run_* directories or policy JSONL files found under {root}")

    rows: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        rows.extend(
            replay_run_dir(
                run_dir,
                policies,
                token_recall_floor=token_recall_floor,
            )
        )
    if not rows:
        raise ValueError(f"no policy JSONL records found under {root}")
    return rows


def write_replay_records_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def format_markdown(summary: dict[str, Any]) -> str:
    policies = summary.get("policies", {})
    lines = [
        "# LeanRepair Strict Replay Audit",
        "",
        f"- Root: `{summary.get('root', '')}`",
        f"- Policies: `{', '.join(sorted(policies))}`",
        f"- Low token-recall floor: `{summary.get('token_recall_floor', 0.2):.2f}`",
        "",
        "## Aggregate",
        "",
        "| Policy | Records | Raw Solved | Strict Solved | Raw Exact | Strict Exact | Strict Nonexact | Exact Given Strict | Raw Degenerate | Lost Under Strict | Strict Retention | Recovered Later |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, row in sorted(policies.items()):
        lines.append(
            f"| {policy} | {row['count']} | {row['raw_solved']} | "
            f"{row['strict_solved']} | {row['raw_exact']} | {row['strict_exact']} | "
            f"{row['strict_not_exact']} | {_pct(row['strict_exact_given_strict'])} | "
            f"{row['raw_degenerate_solved']} | {row['raw_to_strict_loss']} | "
            f"{_pct(row['strict_retention_given_raw'])} | "
            f"{row['recovered_after_degenerate']} |"
        )

    lines.extend(["", "## Raw Degenerate Reasons", ""])
    lines.extend(["| Policy | goal_true | reflexive_equality | low_target_token_recall |", "|---|---:|---:|---:|"])
    for policy, row in sorted(policies.items()):
        reasons = row.get("raw_degenerate_reasons", {})
        lines.append(
            f"| {policy} | {int(reasons.get('goal_true', 0))} | "
            f"{int(reasons.get('reflexive_equality', 0))} | "
            f"{int(reasons.get('low_target_token_recall', 0))} |"
        )

    lines.extend(["", "## By Corruption", ""])
    for policy, row in sorted(policies.items()):
        lines.extend(
            [
                f"### {policy}",
                "",
                "| Corruption | N | Raw Solved | Strict Solved | Strict Exact | Strict Nonexact | Exact Given Strict | Raw Degenerate | Lost | Retention |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for corruption, bucket in row.get("by_corruption", {}).items():
            lines.append(
                f"| {_md(corruption)} | {bucket['count']} | {bucket['raw_solved']} | "
                f"{bucket['strict_solved']} | {bucket['strict_exact']} | "
                f"{bucket['strict_not_exact']} | {_pct(bucket['strict_exact_given_strict'])} | "
                f"{bucket['raw_degenerate_solved']} | {bucket['raw_to_strict_loss']} | "
                f"{_pct(bucket['strict_retention_given_raw'])} |"
            )
        lines.append("")

    lines.extend(["## Raw Solves Rejected By Strict Replay", ""])
    for policy, row in sorted(policies.items()):
        examples = row.get("lost_examples", [])
        lines.extend([f"### {policy}", ""])
        if not examples:
            lines.extend(["No raw solves are rejected by strict replay.", ""])
            continue
        lines.extend(
            [
                "| id | corruption | reason | raw step | raw final goal | target goal |",
                "|---|---|---|---:|---|---|",
            ]
        )
        for ex in examples[:10]:
            lines.append(
                f"| {_md(ex['id'])} | {_md(ex['corruption'])} | {_md(ex['raw_reason'])} | "
                f"{_fmt_step(ex['raw_step_index'])} | {_md(_short(ex['raw_final_goal']))} | "
                f"{_md(_short(ex['target_goal']))} |"
            )
        lines.append("")

    lines.extend(["## Strict Nonexact Accepts", ""])
    for policy, row in sorted(policies.items()):
        examples = row.get("strict_nonexact_examples", [])
        lines.extend([f"### {policy}", ""])
        if not examples:
            lines.extend(["Every strict accepted candidate is exact.", ""])
            continue
        lines.extend(
            [
                "| id | corruption | strict step | strict final header | target header |",
                "|---|---|---:|---|---|",
            ]
        )
        for ex in examples[:10]:
            lines.append(
                f"| {_md(ex['id'])} | {_md(ex['corruption'])} | "
                f"{_fmt_step(ex['strict_step_index'])} | "
                f"{_md(_short(ex['strict_final_header']))} | "
                f"{_md(_short(ex['target_header']))} |"
            )
        lines.append("")

    lines.extend(["## Later Nondegenerate Recoveries", ""])
    for policy, row in sorted(policies.items()):
        examples = row.get("recovered_examples", [])
        lines.extend([f"### {policy}", ""])
        if not examples:
            lines.extend(["No trace contains a later nondegenerate accepted candidate after a degenerate one.", ""])
            continue
        lines.extend(
            [
                "| id | corruption | raw reason | raw step | strict step | strict final goal |",
                "|---|---|---|---:|---:|---|",
            ]
        )
        for ex in examples[:10]:
            lines.append(
                f"| {_md(ex['id'])} | {_md(ex['corruption'])} | {_md(ex['raw_reason'])} | "
                f"{_fmt_step(ex['raw_step_index'])} | {_fmt_step(ex['strict_step_index'])} | "
                f"{_md(_short(ex['strict_final_goal']))} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip()


def _accepted_trace_candidates(
    row: dict[str, Any],
    *,
    token_recall_floor: float,
) -> list[dict[str, Any]]:
    trace = row.get("trace", [])
    if not isinstance(trace, list):
        return []
    candidates: list[dict[str, Any]] = []
    for index, step in enumerate(trace, start=1):
        if not isinstance(step, dict) or not step.get("ok", False):
            continue
        prepared = sda.classify_record(
            {
                "id": row.get("id", ""),
                "policy": row.get("policy", ""),
                "corruption": row.get("corruption", "unknown") or "unknown",
                "ok": True,
                "exact": False,
                "final": step.get("candidate", "") or "",
                "final_header": step.get("candidate", "") or "",
                "target": row.get("target", "") or "",
                "target_header": row.get("target_header", "") or row.get("target", "") or "",
            },
            token_recall_floor=token_recall_floor,
        )
        prepared["step_index"] = index
        candidates.append(prepared)
    return candidates


def _summarize_replays(
    replays: list[dict[str, Any]],
    *,
    max_examples: int,
) -> dict[str, Any]:
    total = len(replays)
    raw_solved = sum(1 for row in replays if row["raw_ok"])
    strict_solved = sum(1 for row in replays if row["strict_ok"])
    raw_exact = sum(1 for row in replays if row["raw_exact"])
    strict_exact = sum(1 for row in replays if row["strict_exact"])
    strict_not_exact = sum(1 for row in replays if row["strict_ok"] and not row["strict_exact"])
    raw_degenerate = sum(1 for row in replays if row["raw_degenerate"])
    raw_to_strict_loss = sum(1 for row in replays if row["raw_ok"] and not row["strict_ok"])
    discarded_steps = sum(int(row["discarded_degenerate_ok_steps"]) for row in replays)
    recovered = sum(1 for row in replays if row["recovered_after_degenerate"])
    changed_output = sum(1 for row in replays if row["changed_accepted_output"])

    by_reason: Counter[str] = Counter(
        str(row["raw_reason"])
        for row in replays
        if row["raw_degenerate"] and row["raw_reason"]
    )
    by_corruption: dict[str, _Bucket] = {}
    for row in replays:
        by_corruption.setdefault(str(row["corruption"]), _Bucket()).add(row)

    lost_examples = [
        _example_json(row)
        for row in sorted(
            (row for row in replays if row["raw_ok"] and not row["strict_ok"]),
            key=lambda item: (
                str(item["raw_reason"]),
                str(item["corruption"]),
                str(item["id"]),
            ),
        )[: max(0, int(max_examples))]
    ]
    recovered_examples = [
        _example_json(row)
        for row in sorted(
            (row for row in replays if row["recovered_after_degenerate"]),
            key=lambda item: (
                str(item["corruption"]),
                str(item["id"]),
            ),
        )[: max(0, int(max_examples))]
    ]
    strict_nonexact_examples = [
        _example_json(row)
        for row in sorted(
            (row for row in replays if row["strict_ok"] and not row["strict_exact"]),
            key=lambda item: (
                str(item["corruption"]),
                str(item["id"]),
            ),
        )[: max(0, int(max_examples))]
    ]

    return {
        "count": int(total),
        "raw_solved": int(raw_solved),
        "strict_solved": int(strict_solved),
        "raw_exact": int(raw_exact),
        "strict_exact": int(strict_exact),
        "strict_not_exact": int(strict_not_exact),
        "raw_degenerate_solved": int(raw_degenerate),
        "raw_to_strict_loss": int(raw_to_strict_loss),
        "discarded_degenerate_ok_steps": int(discarded_steps),
        "recovered_after_degenerate": int(recovered),
        "changed_accepted_output": int(changed_output),
        "raw_solve_rate": _rate(raw_solved, total),
        "strict_solve_rate": _rate(strict_solved, total),
        "raw_exact_rate": _rate(raw_exact, total),
        "strict_exact_rate": _rate(strict_exact, total),
        "strict_exact_given_strict": _rate(strict_exact, strict_solved),
        "raw_degenerate_solved_rate": _rate(raw_degenerate, total),
        "strict_retention_given_raw": _rate(strict_solved, raw_solved),
        "raw_degenerate_reasons": dict(sorted(by_reason.items())),
        "by_corruption": {
            name: bucket.to_json_dict()
            for name, bucket in sorted(by_corruption.items(), key=lambda item: item[0])
        },
        "lost_examples": lost_examples,
        "recovered_examples": recovered_examples,
        "strict_nonexact_examples": strict_nonexact_examples,
    }


class _Bucket:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, row: dict[str, Any]) -> None:
        self.rows.append(row)

    def to_json_dict(self) -> dict[str, Any]:
        total = len(self.rows)
        raw_solved = sum(1 for row in self.rows if row["raw_ok"])
        strict_solved = sum(1 for row in self.rows if row["strict_ok"])
        raw_exact = sum(1 for row in self.rows if row["raw_exact"])
        strict_exact = sum(1 for row in self.rows if row["strict_exact"])
        strict_not_exact = sum(1 for row in self.rows if row["strict_ok"] and not row["strict_exact"])
        raw_degenerate = sum(1 for row in self.rows if row["raw_degenerate"])
        loss = sum(1 for row in self.rows if row["raw_ok"] and not row["strict_ok"])
        recovered = sum(1 for row in self.rows if row["recovered_after_degenerate"])
        return {
            "count": int(total),
            "raw_solved": int(raw_solved),
            "strict_solved": int(strict_solved),
            "raw_exact": int(raw_exact),
            "strict_exact": int(strict_exact),
            "strict_not_exact": int(strict_not_exact),
            "raw_degenerate_solved": int(raw_degenerate),
            "raw_to_strict_loss": int(loss),
            "recovered_after_degenerate": int(recovered),
            "raw_solve_rate": _rate(raw_solved, total),
            "strict_solve_rate": _rate(strict_solved, total),
            "strict_exact_given_strict": _rate(strict_exact, strict_solved),
            "strict_retention_given_raw": _rate(strict_solved, raw_solved),
        }


def _empty_candidate(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "policy": str(row.get("policy", "")),
        "corruption": str(row.get("corruption", "unknown") or "unknown"),
        "ok": False,
        "exact": False,
        "degenerate": False,
        "reason": "",
        "step_index": None,
        "final_header": "",
        "target_header": str(row.get("target_header", "") or row.get("target", "") or ""),
        "final_goal": "",
        "target_goal": "",
    }


def _before_strict(candidate: dict[str, Any], strict: dict[str, Any] | None) -> bool:
    return strict is None or _step_order(candidate) < _step_order(strict)


def _step_order(candidate: dict[str, Any]) -> int:
    index = candidate.get("step_index")
    return int(index) if index is not None else 10**9


def _example_json(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "policy": row["policy"],
        "corruption": row["corruption"],
        "raw_reason": row["raw_reason"],
        "raw_step_index": row["raw_step_index"],
        "strict_step_index": row["strict_step_index"],
        "raw_final_header": row["raw_final_header"],
        "strict_final_header": row["strict_final_header"],
        "target_header": row["target_header"],
        "raw_final_goal": row["raw_final_goal"],
        "strict_final_goal": row["strict_final_goal"],
        "target_goal": row["target_goal"],
    }


def _rate(numer: int, denom: int) -> float:
    return (float(numer) / float(denom)) if denom else 0.0


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _fmt_step(value: object) -> str:
    if value is None:
        return "-"
    return str(value)


def _md(value: object) -> str:
    return str(value).replace("|", "\\|")


def _short(value: str, max_len: int = 120) -> str:
    value = " ".join(str(value).split())
    if len(value) <= max_len:
        return value
    return value[: max_len - 3].rstrip() + "..."


__all__ = [
    "analyze_records",
    "analyze_root",
    "analyze_run_dir",
    "format_markdown",
    "load_jsonl",
    "replay_record",
    "replay_records",
    "replay_root",
    "replay_run_dir",
    "write_replay_records_jsonl",
]
