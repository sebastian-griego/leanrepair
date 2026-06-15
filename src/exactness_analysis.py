from __future__ import annotations

from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from jsonl_io import load_policy_result_objects


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return load_policy_result_objects(path)


def analyze_records(
    records: list[dict[str, Any]],
    *,
    max_examples: int = 20,
) -> dict[str, Any]:
    by_corruption: dict[str, _Bucket] = {}
    drift_examples: list[dict[str, Any]] = []
    similarities: list[float] = []
    token_overlaps: list[float] = []
    solved = 0
    exact = 0
    solved_with_target = 0
    drift = 0
    missing_target = 0

    for row in records:
        prepared = _prepare_record(row)
        solved += int(prepared["ok"])
        exact += int(prepared["exact"])
        solved_with_target += int(prepared["ok"] and prepared["has_target"])
        drift += int(prepared["drift"])
        missing_target += int(prepared["ok"] and not prepared["has_target"])
        if prepared["ok"] and prepared["has_target"]:
            similarities.append(float(prepared["char_similarity"]))
            token_overlaps.append(float(prepared["token_jaccard"]))
        if prepared["drift"]:
            drift_examples.append(prepared)
        bucket = by_corruption.setdefault(str(prepared["corruption"]), _Bucket())
        bucket.add(prepared)

    drift_examples.sort(
        key=lambda item: (
            float(item["char_similarity"]),
            float(item["token_jaccard"]),
            str(item["id"]),
        )
    )
    total = len(records)
    return {
        "count": int(total),
        "solved": int(solved),
        "exact": int(exact),
        "solved_with_target": int(solved_with_target),
        "solved_not_exact": int(drift),
        "solved_missing_target": int(missing_target),
        "solve_rate": _rate(solved, total),
        "exact_rate": _rate(exact, total),
        "exact_given_solved": _rate(exact, solved),
        "drift_given_solved": _rate(drift, solved),
        "avg_header_similarity": mean(similarities) if similarities else None,
        "avg_token_jaccard": mean(token_overlaps) if token_overlaps else None,
        "by_corruption": {
            name: bucket.to_json_dict()
            for name, bucket in sorted(by_corruption.items(), key=lambda item: item[0])
        },
        "drift_examples": [
            _example_json(item)
            for item in drift_examples[: max(0, int(max_examples))]
        ],
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
        "# LeanRepair Exactness Gap",
        "",
        f"- Root: `{summary.get('root', '')}`",
        f"- Policies: `{', '.join(sorted(policies))}`",
        "",
        "## Aggregate",
        "",
        "| Policy | Records | Solved | Exact | Drift | Solve Rate | Exact Rate | Solve-Exact Gap | Exact Given Solved | Drift Given Solved | Avg Header Similarity |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, row in sorted(policies.items()):
        gap = float(row["solve_rate"]) - float(row["exact_rate"])
        lines.append(
            f"| {policy} | {row['count']} | {row['solved']} | {row['exact']} | "
            f"{row['solved_not_exact']} | {_pct(row['solve_rate'])} | "
            f"{_pct(row['exact_rate'])} | {_pct(gap)} | "
            f"{_pct(row['exact_given_solved'])} | "
            f"{_pct(row['drift_given_solved'])} | {_fmt_optional_pct(row['avg_header_similarity'])} |"
        )

    lines.extend(["", "## By Corruption", ""])
    for policy, row in sorted(policies.items()):
        lines.extend(
            [
                f"### {policy}",
                "",
                "| Corruption | N | Solve Rate | Exact Rate | Exact Given Solved | Avg Similarity |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for corruption, bucket in row.get("by_corruption", {}).items():
            lines.append(
                f"| {_md(corruption)} | {bucket['count']} | {_pct(bucket['solve_rate'])} | "
                f"{_pct(bucket['exact_rate'])} | {_pct(bucket['exact_given_solved'])} | "
                f"{_fmt_optional_pct(bucket['avg_header_similarity'])} |"
            )
        lines.append("")

    lines.extend(["## Largest Solved-Not-Exact Drifts", ""])
    for policy, row in sorted(policies.items()):
        examples = row.get("drift_examples", [])
        lines.extend([f"### {policy}", ""])
        if not examples:
            lines.extend(["No solved-not-exact examples.", ""])
            continue
        lines.extend(
            [
                "| id | corruption | similarity | final header | target header |",
                "|---|---|---:|---|---|",
            ]
        )
        for ex in examples[:10]:
            lines.append(
                f"| {_md(ex['id'])} | {_md(ex['corruption'])} | "
                f"{100.0 * ex['char_similarity']:.1f}% | {_md(_short(ex['final_header']))} | "
                f"{_md(_short(ex['target_header']))} |"
            )
        lines.append("")
    return "\n".join(lines)


class _Bucket:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, row: dict[str, Any]) -> None:
        self.rows.append(row)

    def to_json_dict(self) -> dict[str, Any]:
        total = len(self.rows)
        solved = sum(1 for row in self.rows if row["ok"])
        exact = sum(1 for row in self.rows if row["exact"])
        drift = sum(1 for row in self.rows if row["drift"])
        similarities = [
            float(row["char_similarity"])
            for row in self.rows
            if row["ok"] and row["has_target"]
        ]
        token_overlaps = [
            float(row["token_jaccard"])
            for row in self.rows
            if row["ok"] and row["has_target"]
        ]
        return {
            "count": int(total),
            "solved": int(solved),
            "exact": int(exact),
            "solved_not_exact": int(drift),
            "solve_rate": _rate(solved, total),
            "exact_rate": _rate(exact, total),
            "exact_given_solved": _rate(exact, solved),
            "drift_given_solved": _rate(drift, solved),
            "avg_header_similarity": mean(similarities) if similarities else None,
            "avg_token_jaccard": mean(token_overlaps) if token_overlaps else None,
        }


def _prepare_record(row: dict[str, Any]) -> dict[str, Any]:
    ok = bool(row.get("ok", False))
    final_header = _header(row, "final_header", "final")
    target_header = _header(row, "target_header", "target")
    has_target = bool(target_header)
    exact = bool(row.get("exact", False))
    if ok and has_target and final_header == target_header:
        exact = True
    drift = bool(ok and has_target and not exact)
    if ok and has_target:
        char_similarity = _char_similarity(final_header, target_header)
        token_jaccard = _token_jaccard(final_header, target_header)
    else:
        char_similarity = None
        token_jaccard = None
    return {
        "id": str(row.get("id", "")),
        "policy": str(row.get("policy", "")),
        "corruption": str(row.get("corruption", "unknown") or "unknown"),
        "ok": ok,
        "exact": bool(ok and has_target and exact),
        "drift": drift,
        "has_target": has_target,
        "final_header": final_header,
        "target_header": target_header,
        "char_similarity": char_similarity,
        "token_jaccard": token_jaccard,
    }


def _header(row: dict[str, Any], header_key: str, fallback_key: str) -> str:
    value = row.get(header_key)
    if value:
        return str(value).strip()
    return _normalize_header(str(row.get(fallback_key, "") or ""))


def _normalize_header(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if ":=" in text:
        text = text.split(":=", 1)[0]
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return " ".join(lines).strip()


def _char_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    denom = max(len(a), len(b), 1)
    return max(0.0, 1.0 - (_levenshtein(a, b) / float(denom)))


def _token_jaccard(a: str, b: str) -> float:
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens and not b_tokens:
        return 1.0
    return len(a_tokens & b_tokens) / float(len(a_tokens | b_tokens))


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + int(ca != cb),
                )
            )
        previous = current
    return previous[-1]


def _example_json(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "policy": row["policy"],
        "corruption": row["corruption"],
        "final_header": row["final_header"],
        "target_header": row["target_header"],
        "char_similarity": row["char_similarity"],
        "token_jaccard": row["token_jaccard"],
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


__all__ = ["analyze_records", "analyze_root", "analyze_run_dir", "format_markdown", "load_jsonl"]
