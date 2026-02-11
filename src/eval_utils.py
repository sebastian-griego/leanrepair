from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from typing import Any

import lean_check as lc


@dataclass(frozen=True)
class ExperimentRecord:
    item_id: str
    policy: str
    corruption: str
    ok: bool
    steps: int
    elapsed_ms: int
    final: str
    target: str = ""


def normalize_header(text: str) -> str:
    sanitized = lc.sanitize_candidate(text or "")
    return sanitized or ""


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    spread = z * ((p * (1.0 - p) + z * z / (4.0 * total)) / total) ** 0.5
    lo = (centre - spread) / denom
    hi = (centre + spread) / denom
    return max(0.0, lo), min(1.0, hi)


def summarize(records: list[ExperimentRecord]) -> dict[str, Any]:
    total = len(records)
    solved = sum(1 for rec in records if rec.ok)
    exact = sum(1 for rec in records if rec.ok and normalize_header(rec.final) == normalize_header(rec.target))

    success_ci = wilson_interval(solved, total)
    exact_ci = wilson_interval(exact, total)

    by_corruption: dict[str, dict[str, Any]] = {}
    for rec in records:
        bucket = by_corruption.setdefault(
            rec.corruption,
            {
                "count": 0,
                "solved": 0,
                "exact": 0,
            },
        )
        bucket["count"] += 1
        bucket["solved"] += int(rec.ok)
        bucket["exact"] += int(rec.ok and normalize_header(rec.final) == normalize_header(rec.target))

    for bucket in by_corruption.values():
        count = max(1, bucket["count"])
        bucket["solve_rate"] = bucket["solved"] / count
        bucket["exact_rate"] = bucket["exact"] / count
        lo, hi = wilson_interval(bucket["solved"], bucket["count"])
        bucket["solve_rate_ci95"] = [lo, hi]

    step_values = [rec.steps for rec in records]
    elapsed_values = [rec.elapsed_ms for rec in records]

    return {
        "count": total,
        "solved": solved,
        "exact": exact,
        "solve_rate": (solved / total) if total else 0.0,
        "solve_rate_ci95": [success_ci[0], success_ci[1]],
        "exact_rate": (exact / total) if total else 0.0,
        "exact_rate_ci95": [exact_ci[0], exact_ci[1]],
        "avg_steps": mean(step_values) if step_values else 0.0,
        "median_steps": median(step_values) if step_values else 0.0,
        "avg_elapsed_ms": mean(elapsed_values) if elapsed_values else 0.0,
        "by_corruption": dict(sorted(by_corruption.items(), key=lambda kv: kv[0])),
    }


__all__ = ["ExperimentRecord", "normalize_header", "summarize", "wilson_interval"]
