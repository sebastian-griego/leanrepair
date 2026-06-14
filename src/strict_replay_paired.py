from __future__ import annotations

from collections import Counter
from math import exp, lgamma, log
from pathlib import Path
from typing import Any, Iterable

import eval_utils as eu
from jsonl_io import JsonlError
from strict_replay_records import (
    load_records_jsonl as load_strict_replay_records,
    validate_record as validate_strict_replay_record,
)


PAIRED_METRICS = ("raw_ok", "strict_ok", "strict_exact")


def load_records_jsonl(path: Path) -> list[dict[str, Any]]:
    return load_strict_replay_records(path)


def analyze_records(
    records: Iterable[dict[str, Any]],
    *,
    policy_a: str = "heuristic",
    policy_b: str = "research",
    strict_pairs: bool = False,
    max_cases: int = 25,
) -> dict[str, Any]:
    rows = list(records)
    if not rows:
        raise ValueError("no strict replay records found")
    _validate_input_records(rows)
    policy_a = str(policy_a)
    policy_b = str(policy_b)
    by_key = _index_records(rows)
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    a_unpaired: list[dict[str, Any]] = []
    b_unpaired: list[dict[str, Any]] = []
    for key in sorted(by_key):
        bucket = by_key[key]
        a = bucket.get(policy_a)
        b = bucket.get(policy_b)
        if a is not None and b is not None:
            pairs.append((a, b))
        elif a is not None:
            a_unpaired.append(a)
        elif b is not None:
            b_unpaired.append(b)
    if strict_pairs and (a_unpaired or b_unpaired):
        raise ValueError(
            f"unpaired records: {policy_a}-only={len(a_unpaired)}, "
            f"{policy_b}-only={len(b_unpaired)}"
        )
    if not pairs:
        raise ValueError(f"no paired {policy_a}/{policy_b} records found")

    metric_summaries = {
        metric: _paired_metric(pairs, metric) for metric in PAIRED_METRICS
    }
    raw_win_lost = [
        _paired_case(a, b)
        for a, b in pairs
        if bool(b.get("raw_ok")) and not bool(a.get("raw_ok")) and not bool(b.get("strict_ok"))
    ]
    raw_win_lost.sort(key=_case_sort_key)
    raw_win_loss = _raw_win_loss_summary(raw_win_lost)
    b_strict_wins = [
        _paired_case(a, b)
        for a, b in pairs
        if bool(b.get("strict_ok")) and not bool(a.get("strict_ok"))
    ]
    a_strict_wins = [
        _paired_case(a, b)
        for a, b in pairs
        if bool(a.get("strict_ok")) and not bool(b.get("strict_ok"))
    ]
    b_exact_wins = [
        _paired_case(a, b)
        for a, b in pairs
        if bool(b.get("strict_exact")) and not bool(a.get("strict_exact"))
    ]
    for cases in (b_strict_wins, a_strict_wins, b_exact_wins):
        cases.sort(key=_case_sort_key)

    by_corruption: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for a, b in pairs:
        corruption = str(b.get("corruption") or a.get("corruption") or "unknown")
        by_corruption.setdefault(corruption, []).append((a, b))

    return {
        "policy_a": policy_a,
        "policy_b": policy_b,
        "coverage": {
            "policy_a_records": sum(1 for row in rows if str(row.get("policy")) == policy_a),
            "policy_b_records": sum(1 for row in rows if str(row.get("policy")) == policy_b),
            "paired_records": len(pairs),
            "policy_a_unpaired": len(a_unpaired),
            "policy_b_unpaired": len(b_unpaired),
        },
        "metrics": metric_summaries,
        "by_policy": {
            policy_a: _policy_summary((a for a, _ in pairs)),
            policy_b: _policy_summary((b for _, b in pairs)),
        },
        "by_corruption": {
            corruption: {
                metric: _paired_metric(bucket, metric)
                for metric in PAIRED_METRICS
            }
            for corruption, bucket in sorted(by_corruption.items())
        },
        "case_counts": {
            "policy_b_strict_wins": len(b_strict_wins),
            "policy_a_strict_wins": len(a_strict_wins),
            "policy_b_exact_wins": len(b_exact_wins),
            "policy_b_raw_wins_lost_by_strict": len(raw_win_lost),
        },
        "raw_win_loss": raw_win_loss,
        "casebook": {
            "policy_b_strict_wins": b_strict_wins[: max(0, int(max_cases))],
            "policy_a_strict_wins": a_strict_wins[: max(0, int(max_cases))],
            "policy_b_exact_wins": b_exact_wins[: max(0, int(max_cases))],
            "policy_b_raw_wins_lost_by_strict": raw_win_lost[: max(0, int(max_cases))],
        },
        "config": {
            "paired_metrics": list(PAIRED_METRICS),
            "strict_pairs": bool(strict_pairs),
            "max_cases": int(max(0, max_cases)),
        },
    }


def format_markdown(summary: dict[str, Any]) -> str:
    a = summary["policy_a"]
    b = summary["policy_b"]
    coverage = summary["coverage"]
    metrics = summary["metrics"]
    raw = metrics["raw_ok"]
    strict = metrics["strict_ok"]
    exact = metrics["strict_exact"]
    lines = [
        "# LeanRepair Strict Replay Paired Analysis",
        "",
        f"- Baseline policy: `{a}`",
        f"- Compared policy: `{b}`",
        f"- Paired records: `{coverage['paired_records']}`",
        f"- Unpaired records: `{coverage['policy_a_unpaired']}` {a}-only, "
        f"`{coverage['policy_b_unpaired']}` {b}-only",
        f"- Raw solve lift: `{_pp(raw['policy_b_lift'])}` "
        f"({b} only `{raw['policy_b_only']}`, {a} only `{raw['policy_a_only']}`)",
        f"- Strict solve lift: `{_pp(strict['policy_b_lift'])}` "
        f"({b} only `{strict['policy_b_only']}`, {a} only `{strict['policy_a_only']}`)",
        f"- Strict exact lift: `{_pp(exact['policy_b_lift'])}` "
        f"({b} only `{exact['policy_b_only']}`, {a} only `{exact['policy_a_only']}`)",
        f"- Strict solve sign-test p-value: `{strict['paired_exact_sign_p_two_sided']:.3e}`",
        f"- Strict exact sign-test p-value: `{exact['paired_exact_sign_p_two_sided']:.3e}`",
        f"- Compared raw wins lost under strict replay: "
        f"`{summary['raw_win_loss']['total']}`",
        "",
        "## Metric Table",
        "",
        "| Metric | Both | Baseline only | Compared only | Neither | Baseline rate | Compared rate | Lift | p-value |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for metric in PAIRED_METRICS:
        row = metrics[metric]
        lines.append(
            f"| `{metric}` | {row['both_success']} | {row['policy_a_only']} | "
            f"{row['policy_b_only']} | {row['neither_success']} | "
            f"{_pct(row['policy_a_rate'])} | {_pct(row['policy_b_rate'])} | "
            f"{_pp(row['policy_b_lift'])} | {row['paired_exact_sign_p_two_sided']:.3e} |"
        )

    lines.extend(
        [
            "",
            "## Policy Strictness",
            "",
            "| Policy | Raw solved | Strict solved | Strict exact | Raw degenerate | Lost under strict | Strict retention |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for policy, row in summary["by_policy"].items():
        lines.append(
            f"| `{policy}` | {row['raw_ok']} | {row['strict_ok']} | "
            f"{row['strict_exact']} | {row['raw_degenerate']} | "
            f"{row['raw_to_strict_loss']} | {_pct(row['strict_retention'])} |"
        )

    lines.extend(
        [
            "",
            "## By Corruption",
            "",
            "| Corruption | N | Strict baseline only | Strict compared only | Strict lift | Strict exact lift | Strict p-value |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for corruption, bucket in summary["by_corruption"].items():
        strict_row = bucket["strict_ok"]
        exact_row = bucket["strict_exact"]
        lines.append(
            f"| `{_md(corruption)}` | {strict_row['n_total']} | "
            f"{strict_row['policy_a_only']} | {strict_row['policy_b_only']} | "
            f"{_pp(strict_row['policy_b_lift'])} | "
            f"{_pp(exact_row['policy_b_lift'])} | "
            f"{strict_row['paired_exact_sign_p_two_sided']:.3e} |"
        )

    _append_raw_win_loss_breakdown(lines, summary["raw_win_loss"])
    _append_case_table(
        lines,
        f"{b} Strict Wins",
        summary["casebook"]["policy_b_strict_wins"],
    )
    _append_case_table(
        lines,
        f"{a} Strict Wins",
        summary["casebook"]["policy_a_strict_wins"],
    )
    _append_case_table(
        lines,
        f"{b} Strict Exact Wins",
        summary["casebook"]["policy_b_exact_wins"],
    )
    _append_case_table(
        lines,
        f"{b} Raw Wins Lost By Strict Replay",
        summary["casebook"]["policy_b_raw_wins_lost_by_strict"],
    )
    return "\n".join(lines).rstrip()


def _index_records(
    rows: Iterable[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    by_key: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    first_rows: dict[tuple[str, str, str], int] = {}
    for row_no, row in enumerate(rows, start=1):
        key = (str(row.get("run", "")), str(row.get("id", "")))
        policy = str(row.get("policy", ""))
        full_key = (key[0], key[1], policy)
        bucket = by_key.setdefault(key, {})
        if policy in bucket:
            raise JsonlError(
                "duplicate strict replay row "
                f"run={key[0]!r}, id={key[1]!r}, policy={policy!r} "
                f"at input row {row_no}; first seen at input row {first_rows[full_key]}"
            )
        bucket[policy] = row
        first_rows[full_key] = row_no
    return by_key


def _validate_input_records(rows: Iterable[dict[str, Any]]) -> None:
    for row_no, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise JsonlError(
                f"expected input strict replay record {row_no} to be dict, "
                f"got {type(row).__name__}"
            )
        validate_strict_replay_record(
            row,
            path="input strict replay records",
            line_no=row_no,
        )


def _paired_metric(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    metric: str,
) -> dict[str, Any]:
    both = a_only = b_only = neither = 0
    for a, b in pairs:
        a_ok = bool(a.get(metric))
        b_ok = bool(b.get(metric))
        if a_ok and b_ok:
            both += 1
        elif a_ok and not b_ok:
            a_only += 1
        elif b_ok and not a_ok:
            b_only += 1
        else:
            neither += 1
    total = len(pairs)
    a_successes = both + a_only
    b_successes = both + b_only
    a_ci = eu.wilson_interval(a_successes, total)
    b_ci = eu.wilson_interval(b_successes, total)
    discordant = a_only + b_only
    return {
        "metric": metric,
        "n_total": total,
        "both_success": both,
        "policy_a_only": a_only,
        "policy_b_only": b_only,
        "neither_success": neither,
        "policy_a_successes": a_successes,
        "policy_b_successes": b_successes,
        "policy_a_rate": a_successes / float(total) if total else 0.0,
        "policy_b_rate": b_successes / float(total) if total else 0.0,
        "policy_a_rate_ci95": list(a_ci),
        "policy_b_rate_ci95": list(b_ci),
        "policy_b_lift": (b_successes - a_successes) / float(total) if total else 0.0,
        "discordant_total": discordant,
        "policy_b_win_rate_on_discordant": b_only / float(discordant) if discordant else 0.5,
        "paired_exact_sign_p_two_sided": _exact_sign_p(wins=b_only, losses=a_only),
    }


def _policy_summary(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    raw_ok = sum(1 for row in rows if bool(row.get("raw_ok")))
    strict_ok = sum(1 for row in rows if bool(row.get("strict_ok")))
    strict_exact = sum(1 for row in rows if bool(row.get("strict_exact")))
    raw_degenerate = sum(1 for row in rows if bool(row.get("raw_degenerate")))
    raw_to_strict_loss = sum(
        1 for row in rows if bool(row.get("raw_ok")) and not bool(row.get("strict_ok"))
    )
    return {
        "records": len(rows),
        "raw_ok": raw_ok,
        "strict_ok": strict_ok,
        "strict_exact": strict_exact,
        "raw_degenerate": raw_degenerate,
        "raw_to_strict_loss": raw_to_strict_loss,
        "strict_retention": strict_ok / float(raw_ok) if raw_ok else 0.0,
    }


def _raw_win_loss_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(cases)
    reason_counts: Counter[str] = Counter()
    corruption_counts: Counter[str] = Counter()
    reason_corruption_counts: Counter[tuple[str, str]] = Counter()
    for case in cases:
        reason = _case_reason(case)
        corruption = str(case.get("corruption") or "unknown")
        reason_counts[reason] += 1
        corruption_counts[corruption] += 1
        reason_corruption_counts[(reason, corruption)] += 1
    return {
        "total": total,
        "by_reason": _counter_rows(reason_counts, total),
        "by_corruption": _counter_rows(corruption_counts, total),
        "by_reason_and_corruption": [
            {
                "reason": reason,
                "corruption": corruption,
                "count": count,
                "share": count / float(total) if total else 0.0,
            }
            for (reason, corruption), count in sorted(
                reason_corruption_counts.items(),
                key=lambda item: (-item[1], item[0][0], item[0][1]),
            )
        ],
    }


def _case_reason(case: dict[str, Any]) -> str:
    policy_b = case.get("policy_b", {})
    reason = policy_b.get("raw_reason") if isinstance(policy_b, dict) else ""
    reason = str(reason or "").strip()
    return reason or "unknown"


def _counter_rows(counter: Counter[str], total: int) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "count": count,
            "share": count / float(total) if total else 0.0,
        }
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _paired_case(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    return {
        "run": str(b.get("run") or a.get("run") or ""),
        "id": str(b.get("id") or a.get("id") or ""),
        "corruption": str(b.get("corruption") or a.get("corruption") or "unknown"),
        "policy_a": _compact_record(a),
        "policy_b": _compact_record(b),
        "target_header": str(b.get("target_header") or a.get("target_header") or ""),
        "target_goal": str(b.get("target_goal") or a.get("target_goal") or ""),
    }


def _compact_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy": str(row.get("policy", "")),
        "raw_ok": bool(row.get("raw_ok")),
        "strict_ok": bool(row.get("strict_ok")),
        "strict_exact": bool(row.get("strict_exact")),
        "raw_degenerate": bool(row.get("raw_degenerate")),
        "raw_reason": str(row.get("raw_reason", "")),
        "raw_step_index": row.get("raw_step_index"),
        "strict_step_index": row.get("strict_step_index"),
        "raw_final_header": str(row.get("raw_final_header", "")),
        "strict_final_header": str(row.get("strict_final_header", "")),
    }


def _exact_sign_p(*, wins: int, losses: int) -> float:
    wins = int(wins)
    losses = int(losses)
    if wins < 0 or losses < 0:
        raise ValueError("wins and losses must be nonnegative")
    n = wins + losses
    if n == 0:
        return 1.0
    tail = min(wins, losses)
    log_probs = [_log_binomial_half_pmf(k, n) for k in range(tail + 1)]
    max_log = max(log_probs)
    one_tail = exp(max_log) * sum(exp(value - max_log) for value in log_probs)
    return min(1.0, 2.0 * one_tail)


def _log_binomial_half_pmf(k: int, n: int) -> float:
    return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1) - n * log(2.0)


def _append_case_table(
    lines: list[str],
    title: str,
    cases: list[dict[str, Any]],
) -> None:
    lines.extend(["", f"## {title}", ""])
    if not cases:
        lines.append("No cases.")
        return
    lines.append(
        "| run | id | corruption | baseline raw/strict/exact | compared raw/strict/exact | compared reason | compared strict header |"
    )
    lines.append("|---|---|---|---:|---:|---|---|")
    for row in cases:
        a = row["policy_a"]
        b = row["policy_b"]
        lines.append(
            f"| {_md(row['run'])} | {_md(row['id'])} | {_md(row['corruption'])} | "
            f"{_flags(a)} | {_flags(b)} | {_md(_short(b.get('raw_reason', '')))} | "
            f"{_md(_short(b.get('strict_final_header', '') or b.get('raw_final_header', '')))} |"
        )


def _append_raw_win_loss_breakdown(
    lines: list[str],
    summary: dict[str, Any],
) -> None:
    lines.extend(
        [
            "",
            "## Raw Wins Lost By Strict Replay Breakdown",
            "",
            "Raw wins lost by strict replay are cases where the compared policy "
            "solved under raw Lean-ok, the baseline did not, and strict replay "
            "rejected the compared output.",
            "",
            f"- Total lost compared-policy raw wins: `{summary['total']}`",
            "",
            "| Rejection reason | Count | Share |",
            "|---|---:|---:|",
        ]
    )
    for row in summary["by_reason"]:
        lines.append(
            f"| `{_md(row['name'])}` | {row['count']} | {_pct(row['share'])} |"
        )
    if not summary["by_reason"]:
        lines.append("| - | 0 | 0.0% |")

    lines.extend(
        [
            "",
            "| Corruption | Count | Share |",
            "|---|---:|---:|",
        ]
    )
    for row in summary["by_corruption"]:
        lines.append(
            f"| `{_md(row['name'])}` | {row['count']} | {_pct(row['share'])} |"
        )
    if not summary["by_corruption"]:
        lines.append("| - | 0 | 0.0% |")

    lines.extend(
        [
            "",
            "| Rejection reason | Corruption | Count | Share |",
            "|---|---|---:|---:|",
        ]
    )
    for row in summary["by_reason_and_corruption"]:
        lines.append(
            f"| `{_md(row['reason'])}` | `{_md(row['corruption'])}` | "
            f"{row['count']} | {_pct(row['share'])} |"
        )
    if not summary["by_reason_and_corruption"]:
        lines.append("| - | - | 0 | 0.0% |")


def _case_sort_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (str(row.get("corruption", "")), str(row.get("run", "")), str(row.get("id", "")))


def _flags(row: dict[str, Any]) -> str:
    return "/".join(
        _yes_no(bool(row.get(name)))
        for name in ("raw_ok", "strict_ok", "strict_exact")
    )


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _pp(value: float) -> str:
    return f"{100.0 * float(value):+.1f} pp"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


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
]
