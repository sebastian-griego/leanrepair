from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable

from strict_replay_records import (
    load_records_jsonl as load_strict_replay_records,
    validate_records as validate_strict_replay_records,
)


INTERESTING_FLAGS = (
    "raw_to_strict_loss",
    "strict_nonexact_accept",
    "recovered_after_degenerate",
    "changed_accepted_output",
)


def load_records_jsonl(path: Path) -> list[dict[str, Any]]:
    return load_strict_replay_records(path)


def analyze_records(
    records: Iterable[dict[str, Any]],
    *,
    max_cases: int = 25,
) -> dict[str, Any]:
    rows = [_annotate_case(row) for row in validate_strict_replay_records(records)]
    if not rows:
        raise ValueError("no strict replay records found")

    policy_counts = Counter(str(row["policy"]) for row in rows)
    primary_counts = Counter(str(row["primary_case"]) for row in rows)
    flag_counts = Counter(flag for row in rows for flag in row["case_flags"])
    by_policy: dict[str, Counter[str]] = {}
    by_corruption: dict[str, Counter[str]] = {}
    loss_reasons = Counter(
        str(row.get("raw_reason") or "unknown")
        for row in rows
        if "raw_to_strict_loss" in row["case_flags"]
    )
    for row in rows:
        policy = str(row["policy"])
        corruption = str(row["corruption"])
        by_policy.setdefault(policy, Counter())[str(row["primary_case"])] += 1
        by_corruption.setdefault(corruption, Counter())[str(row["primary_case"])] += 1

    focused = [
        row for row in rows if any(flag in row["case_flags"] for flag in INTERESTING_FLAGS)
    ]
    focused.sort(key=_case_sort_key)

    return {
        "dataset": {
            "records": int(len(rows)),
            "focused_cases": int(len(focused)),
            "policies": dict(sorted(policy_counts.items())),
        },
        "primary_case_counts": dict(sorted(primary_counts.items())),
        "flag_counts": dict(sorted(flag_counts.items())),
        "by_policy": {
            policy: dict(sorted(counter.items()))
            for policy, counter in sorted(by_policy.items())
        },
        "by_corruption": {
            corruption: dict(sorted(counter.items()))
            for corruption, counter in sorted(by_corruption.items())
        },
        "raw_loss_reasons": dict(sorted(loss_reasons.items())),
        "casebook": {
            "raw_to_strict_losses": _top_cases(
                (row for row in rows if "raw_to_strict_loss" in row["case_flags"]),
                max_cases=max_cases,
            ),
            "strict_nonexact_accepts": _top_cases(
                (row for row in rows if "strict_nonexact_accept" in row["case_flags"]),
                max_cases=max_cases,
            ),
            "recoveries_after_degenerate": _top_cases(
                (row for row in rows if "recovered_after_degenerate" in row["case_flags"]),
                max_cases=max_cases,
            ),
            "changed_outputs": _top_cases(
                (row for row in rows if "changed_accepted_output" in row["case_flags"]),
                max_cases=max_cases,
            ),
        },
        "focused_cases": focused,
        "config": {
            "max_cases": int(max(0, max_cases)),
            "interesting_flags": list(INTERESTING_FLAGS),
        },
    }


def format_markdown(summary: dict[str, Any]) -> str:
    dataset = summary["dataset"]
    lines = [
        "# LeanRepair Strict Replay Casebook",
        "",
        f"- Records: {dataset['records']}",
        f"- Focused cases: {dataset['focused_cases']}",
        f"- Policies: `{', '.join(sorted(dataset['policies']))}`",
        "",
        "## Primary Case Counts",
        "",
        "| case | count |",
        "|---|---:|",
    ]
    for name, count in summary["primary_case_counts"].items():
        lines.append(f"| `{_md(name)}` | {count} |")

    lines.extend(["", "## Flag Counts", "", "| flag | count |", "|---|---:|"])
    for name, count in summary["flag_counts"].items():
        lines.append(f"| `{_md(name)}` | {count} |")

    lines.extend(["", "## Raw Loss Reasons", "", "| reason | count |", "|---|---:|"])
    if summary["raw_loss_reasons"]:
        for name, count in summary["raw_loss_reasons"].items():
            lines.append(f"| `{_md(name)}` | {count} |")
    else:
        lines.append("| none | 0 |")

    _append_case_table(
        lines,
        "Raw Solves Lost Under Strict Replay",
        summary["casebook"]["raw_to_strict_losses"],
        columns=("raw_reason", "raw_step_index", "raw_final_goal", "target_goal"),
    )
    _append_case_table(
        lines,
        "Strict Nonexact Accepts",
        summary["casebook"]["strict_nonexact_accepts"],
        columns=("strict_step_index", "strict_final_header", "target_header"),
    )
    _append_case_table(
        lines,
        "Recoveries After Degenerate Raw Candidates",
        summary["casebook"]["recoveries_after_degenerate"],
        columns=("raw_reason", "raw_step_index", "strict_step_index", "strict_final_goal"),
    )
    _append_case_table(
        lines,
        "Changed Accepted Outputs",
        summary["casebook"]["changed_outputs"],
        columns=("raw_reason", "raw_step_index", "strict_step_index", "strict_final_header"),
    )
    return "\n".join(lines).rstrip()


def write_cases_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _annotate_case(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    flags: list[str] = []
    if bool(row.get("raw_ok")) and not bool(row.get("strict_ok")):
        flags.append("raw_to_strict_loss")
    if bool(row.get("strict_ok")) and not bool(row.get("strict_exact")):
        flags.append("strict_nonexact_accept")
    if bool(row.get("recovered_after_degenerate")):
        flags.append("recovered_after_degenerate")
    if bool(row.get("changed_accepted_output")):
        flags.append("changed_accepted_output")
    out["case_flags"] = flags
    out["primary_case"] = _primary_case(row, flags)
    return out


def _primary_case(row: dict[str, Any], flags: list[str]) -> str:
    if "raw_to_strict_loss" in flags:
        return "raw_to_strict_loss"
    if "recovered_after_degenerate" in flags:
        return "recovered_after_degenerate"
    if "strict_nonexact_accept" in flags:
        return "strict_nonexact_accept"
    if bool(row.get("strict_exact")):
        return "strict_exact_accept"
    if bool(row.get("raw_ok")):
        return "raw_ok_other"
    return "unsolved"


def _top_cases(
    rows: Iterable[dict[str, Any]],
    *,
    max_cases: int,
) -> list[dict[str, Any]]:
    out = list(rows)
    out.sort(key=_case_sort_key)
    return out[: max(0, int(max_cases))]


def _case_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(row.get("policy", "")),
        str(row.get("primary_case", "")),
        str(row.get("raw_reason", "")),
        str(row.get("corruption", "")),
        str(row.get("run", "")),
        str(row.get("id", "")),
    )


def _append_case_table(
    lines: list[str],
    title: str,
    cases: list[dict[str, Any]],
    *,
    columns: tuple[str, ...],
) -> None:
    lines.extend(["", f"## {title}", ""])
    if not cases:
        lines.append("No cases.")
        return
    header = ["run", "policy", "id", "corruption", *columns]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join("---" for _ in header) + "|")
    for row in cases:
        values = [_short(row.get(column, "")) for column in header]
        lines.append("| " + " | ".join(_md(value) for value in values) + " |")


def _short(value: object, max_len: int = 90) -> str:
    if value is None:
        return "-"
    text = " ".join(str(value).split())
    if text == "":
        return "-"
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _md(value: object) -> str:
    return str(value).replace("|", "\\|")


__all__ = [
    "analyze_records",
    "format_markdown",
    "load_records_jsonl",
    "write_cases_jsonl",
]
