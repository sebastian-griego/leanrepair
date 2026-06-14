from __future__ import annotations

from collections import Counter
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


DEGENERATE_REASONS = (
    "goal_true",
    "reflexive_equality",
    "low_target_token_recall",
)


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
    total = len(records)
    solved = 0
    exact = 0
    degenerate = 0
    solved_with_target = 0
    token_recalls: list[float] = []
    binder_retention: list[float] = []
    by_reason: Counter[str] = Counter()
    by_corruption: dict[str, _Bucket] = {}
    examples: list[dict[str, Any]] = []

    for row in records:
        prepared = _prepare_record(row, token_recall_floor=token_recall_floor)
        solved += int(prepared["ok"])
        exact += int(prepared["exact"])
        degenerate += int(prepared["degenerate"])
        solved_with_target += int(prepared["ok"] and prepared["has_target"])
        if prepared["ok"] and prepared["has_target"]:
            token_recalls.append(float(prepared["target_token_recall"]))
            binder_retention.append(float(prepared["binder_retention"]))
        if prepared["degenerate"]:
            by_reason[str(prepared["reason"])] += 1
            examples.append(prepared)

        bucket = by_corruption.setdefault(str(prepared["corruption"]), _Bucket())
        bucket.add(prepared)

    examples.sort(
        key=lambda item: (
            float(item["target_token_recall"]),
            float(item["binder_retention"]),
            str(item["reason"]),
            str(item["id"]),
        )
    )
    drift = solved - exact
    nondegenerate_solved = solved - degenerate
    return {
        "count": int(total),
        "solved": int(solved),
        "exact": int(exact),
        "solved_not_exact": int(drift),
        "degenerate_solved": int(degenerate),
        "nondegenerate_solved": int(nondegenerate_solved),
        "solved_with_target": int(solved_with_target),
        "solve_rate": _rate(solved, total),
        "exact_rate": _rate(exact, total),
        "degenerate_solved_rate": _rate(degenerate, total),
        "nondegenerate_solved_rate": _rate(nondegenerate_solved, total),
        "degenerate_given_solved": _rate(degenerate, solved),
        "degenerate_given_drift": _rate(degenerate, drift),
        "avg_target_token_recall": mean(token_recalls) if token_recalls else None,
        "avg_binder_retention": mean(binder_retention) if binder_retention else None,
        "degenerate_reasons": dict(sorted(by_reason.items())),
        "by_corruption": {
            name: bucket.to_json_dict()
            for name, bucket in sorted(by_corruption.items(), key=lambda item: item[0])
        },
        "degenerate_examples": [
            _example_json(item)
            for item in examples[: max(0, int(max_examples))]
        ],
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


def format_markdown(summary: dict[str, Any]) -> str:
    policies = summary.get("policies", {})
    lines = [
        "# LeanRepair Semantic Drift Audit",
        "",
        f"- Root: `{summary.get('root', '')}`",
        f"- Policies: `{', '.join(sorted(policies))}`",
        f"- Low token-recall floor: `{summary.get('token_recall_floor', 0.2):.2f}`",
        "",
        "## Aggregate",
        "",
        "| Policy | Records | Solved | Exact | Degenerate Solved | Nondegenerate Solved | Degenerate Given Solved | Avg Target Token Recall | Avg Binder Retention |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, row in sorted(policies.items()):
        lines.append(
            f"| {policy} | {row['count']} | {row['solved']} | {row['exact']} | "
            f"{row['degenerate_solved']} | {row['nondegenerate_solved']} | "
            f"{_pct(row['degenerate_given_solved'])} | "
            f"{_fmt_optional_pct(row['avg_target_token_recall'])} | "
            f"{_fmt_optional_pct(row['avg_binder_retention'])} |"
        )

    lines.extend(["", "## Degenerate Reasons", ""])
    lines.extend(["| Policy | goal_true | reflexive_equality | low_target_token_recall |", "|---|---:|---:|---:|"])
    for policy, row in sorted(policies.items()):
        reasons = row.get("degenerate_reasons", {})
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
                "| Corruption | N | Solved | Exact | Degenerate | Degenerate Given Solved | Avg Token Recall |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for corruption, bucket in row.get("by_corruption", {}).items():
            lines.append(
                f"| {_md(corruption)} | {bucket['count']} | {bucket['solved']} | "
                f"{bucket['exact']} | {bucket['degenerate_solved']} | "
                f"{_pct(bucket['degenerate_given_solved'])} | "
                f"{_fmt_optional_pct(bucket['avg_target_token_recall'])} |"
            )
        lines.append("")

    lines.extend(["## Most Severe Degenerate Solves", ""])
    for policy, row in sorted(policies.items()):
        examples = row.get("degenerate_examples", [])
        lines.extend([f"### {policy}", ""])
        if not examples:
            lines.extend(["No degenerate solved examples.", ""])
            continue
        lines.extend(
            [
                "| id | corruption | reason | token recall | final goal | target goal |",
                "|---|---|---|---:|---|---|",
            ]
        )
        for ex in examples[:10]:
            lines.append(
                f"| {_md(ex['id'])} | {_md(ex['corruption'])} | {_md(ex['reason'])} | "
                f"{_pct(ex['target_token_recall'])} | {_md(_short(ex['final_goal']))} | "
                f"{_md(_short(ex['target_goal']))} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip()


class _Bucket:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, row: dict[str, Any]) -> None:
        self.rows.append(row)

    def to_json_dict(self) -> dict[str, Any]:
        total = len(self.rows)
        solved = sum(1 for row in self.rows if row["ok"])
        exact = sum(1 for row in self.rows if row["exact"])
        degenerate = sum(1 for row in self.rows if row["degenerate"])
        recalls = [
            float(row["target_token_recall"])
            for row in self.rows
            if row["ok"] and row["has_target"]
        ]
        retentions = [
            float(row["binder_retention"])
            for row in self.rows
            if row["ok"] and row["has_target"]
        ]
        return {
            "count": int(total),
            "solved": int(solved),
            "exact": int(exact),
            "degenerate_solved": int(degenerate),
            "nondegenerate_solved": int(solved - degenerate),
            "solve_rate": _rate(solved, total),
            "exact_rate": _rate(exact, total),
            "degenerate_solved_rate": _rate(degenerate, total),
            "degenerate_given_solved": _rate(degenerate, solved),
            "avg_target_token_recall": mean(recalls) if recalls else None,
            "avg_binder_retention": mean(retentions) if retentions else None,
        }


def _prepare_record(row: dict[str, Any], *, token_recall_floor: float) -> dict[str, Any]:
    ok = bool(row.get("ok", False))
    final_header = _header(row, "final_header", "final")
    target_header = _header(row, "target_header", "target")
    final_goal = _goal(final_header)
    target_goal = _goal(target_header)
    has_target = bool(target_goal)
    exact = bool(row.get("exact", False))
    if ok and has_target and final_header == target_header:
        exact = True

    target_token_recall = _token_recall(final_goal, target_goal) if ok and has_target else 0.0
    binder_retention = _binder_retention(final_header, target_header) if ok and has_target else 0.0
    reason = _degenerate_reason(
        ok=ok,
        exact=bool(ok and has_target and exact),
        final_goal=final_goal,
        target_goal=target_goal,
        token_recall=target_token_recall,
        token_recall_floor=token_recall_floor,
    )
    return {
        "id": str(row.get("id", "")),
        "policy": str(row.get("policy", "")),
        "corruption": str(row.get("corruption", "unknown") or "unknown"),
        "ok": ok,
        "exact": bool(ok and has_target and exact),
        "degenerate": reason is not None,
        "reason": reason or "",
        "has_target": has_target,
        "final_header": final_header,
        "target_header": target_header,
        "final_goal": final_goal,
        "target_goal": target_goal,
        "target_token_recall": float(target_token_recall),
        "binder_retention": float(binder_retention),
    }


def _degenerate_reason(
    *,
    ok: bool,
    exact: bool,
    final_goal: str,
    target_goal: str,
    token_recall: float,
    token_recall_floor: float,
) -> str | None:
    if not ok or exact:
        return None
    normalized_goal = _normalize_spaces(final_goal)
    if normalized_goal == "True" and _normalize_spaces(target_goal) != "True":
        return "goal_true"
    if _is_reflexive_equality(normalized_goal) and not _is_reflexive_equality(_normalize_spaces(target_goal)):
        return "reflexive_equality"
    if target_goal and token_recall < float(token_recall_floor):
        return "low_target_token_recall"
    return None


def _header(row: dict[str, Any], header_key: str, fallback_key: str) -> str:
    value = row.get(header_key)
    if value:
        return _normalize_header(str(value))
    return _normalize_header(str(row.get(fallback_key, "") or ""))


def _normalize_header(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if ":=" in text:
        text = text.split(":=", 1)[0]
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return " ".join(lines).strip()


def _goal(header: str) -> str:
    colon_idx = _find_top_level_colon(header)
    if colon_idx == -1:
        return ""
    return _normalize_spaces(header[colon_idx + 1 :])


def _find_top_level_colon(text: str) -> int:
    depth = 0
    for idx, ch in enumerate(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        elif ch == ":" and depth == 0:
            return idx
    return -1


def _token_recall(final_goal: str, target_goal: str) -> float:
    target = set(_tokens(target_goal))
    if not target:
        return 0.0
    final = set(_tokens(final_goal))
    return len(target & final) / float(len(target))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[^\W\d]\w*'?|[0-9]+|->|=>|:=|[=<>+\-*/%]+", text)


def _binder_retention(final_header: str, target_header: str) -> float:
    target = _binder_count(target_header)
    if target == 0:
        return 1.0
    return min(1.0, _binder_count(final_header) / float(target))


def _binder_count(header: str) -> int:
    colon_idx = _find_top_level_colon(header)
    prefix = header if colon_idx == -1 else header[:colon_idx]
    return sum(1 for _match in re.finditer(r"[\(\{\[][^\)\}\]]+[\)\}\]]", prefix))


def _is_reflexive_equality(goal: str) -> bool:
    parts = goal.split("=")
    if len(parts) != 2:
        return False
    left = _normalize_expr(parts[0])
    right = _normalize_expr(parts[1])
    return bool(left) and left == right


def _normalize_expr(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def _normalize_spaces(text: str) -> str:
    return " ".join(str(text).split())


def _example_json(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "policy": row["policy"],
        "corruption": row["corruption"],
        "reason": row["reason"],
        "final_header": row["final_header"],
        "target_header": row["target_header"],
        "final_goal": row["final_goal"],
        "target_goal": row["target_goal"],
        "target_token_recall": row["target_token_recall"],
        "binder_retention": row["binder_retention"],
    }


def _rate(numer: int, denom: int) -> float:
    return (float(numer) / float(denom)) if denom else 0.0


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _fmt_optional_pct(value: Any) -> str:
    if value is None:
        return "-"
    return _pct(float(value))


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
]
