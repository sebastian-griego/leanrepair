from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import lean_check as lc
import semantic_drift_analysis as sda


@dataclass(frozen=True)
class AcceptanceDecision:
    accepted: bool
    reason: str = ""


AcceptanceFn = Callable[[str, lc.CheckResult], bool | AcceptanceDecision]


def accept_lean_ok(candidate: str, result: lc.CheckResult) -> AcceptanceDecision:
    del candidate
    return AcceptanceDecision(accepted=bool(result.ok), reason="lean_ok" if result.ok else "")


def strict_acceptance_for_target(
    target: str,
    *,
    token_recall_floor: float = 0.2,
) -> AcceptanceFn:
    def _accept(candidate: str, result: lc.CheckResult) -> AcceptanceDecision:
        if not result.ok:
            return AcceptanceDecision(False, "")
        row = sda.classify_record(
            {
                "ok": True,
                "exact": False,
                "final": candidate,
                "final_header": candidate,
                "target": target,
                "target_header": target,
            },
            token_recall_floor=token_recall_floor,
        )
        if row["degenerate"]:
            return AcceptanceDecision(False, str(row["reason"]))
        if row["exact"]:
            return AcceptanceDecision(True, "exact")
        return AcceptanceDecision(True, "nondegenerate")

    return _accept


def normalize_decision(value: bool | AcceptanceDecision) -> AcceptanceDecision:
    if isinstance(value, AcceptanceDecision):
        return value
    return AcceptanceDecision(accepted=bool(value), reason="accepted" if value else "")


__all__ = [
    "AcceptanceDecision",
    "AcceptanceFn",
    "accept_lean_ok",
    "normalize_decision",
    "strict_acceptance_for_target",
]
