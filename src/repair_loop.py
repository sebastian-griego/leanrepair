from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Callable, List, Sequence

import lean_check as lc
from lean_errors import ErrorInfo


@dataclass(frozen=True)
class TraceStep:
    candidate: str
    result: lc.CheckResult


@dataclass
class Trace:
    steps: List[TraceStep] = field(default_factory=list)


PolicyOutput = str | Sequence[str]
PolicyFn = Callable[[str, str, str, lc.CheckResult], PolicyOutput]


def repair_one(
    nl: str,
    ctx: str,
    candidate0: str,
    Tmax: int,
    timeout_s: float,
    policy: PolicyFn,
) -> Trace:
    trace = Trace()
    if Tmax <= 0:
        return trace

    queue: list[str] = [candidate0 or ""]
    seen: set[str] = set()
    queued: set[str] = set()

    while queue and len(trace.steps) < Tmax:
        current = queue.pop(0)
        sanitized = lc.sanitize_candidate(current)
        if sanitized is None:
            result = lc.CheckResult(
                ok=False,
                errors=[ErrorInfo(message="candidate rejected", kind="other")],
                raw="",
                elapsed_ms=0,
                timed_out=False,
            )
            trace.steps.append(TraceStep(candidate=current, result=result))
            continue

        theorem = lc.build_theorem(sanitized)
        if theorem in seen:
            continue
        seen.add(theorem)
        queued.discard(theorem)

        result = lc.lean_check(ctx, theorem, timeout_s)
        trace.steps.append(TraceStep(candidate=theorem, result=result))

        if result.ok:
            break

        for proposal in _normalize_policy_output(policy(nl, ctx, sanitized, result)):
            proposed = lc.sanitize_candidate(proposal)
            if proposed is None:
                continue
            proposed_theorem = lc.build_theorem(proposed)
            if proposed_theorem in seen or proposed_theorem in queued:
                continue
            queue.append(proposed)
            queued.add(proposed_theorem)

    return trace


def default_policy(nl: str, ctx: str, candidate: str, result: lc.CheckResult) -> str:
    del nl, ctx

    if not result.errors:
        return candidate

    primary = result.errors[0]
    if primary.kind == "unknown_identifier":
        ident = _extract_unknown_ident(primary.message) or _infer_simple_ident(candidate)
        if ident and ident[0].islower():
            binder_type = _infer_binder_type(candidate, ident)
            return _add_binder(candidate, ident, binder_type)

    if primary.kind == "parse_error":
        return _fix_parse(candidate)

    if primary.kind == "not_proposition":
        repaired = _repair_not_proposition(candidate)
        if repaired != candidate:
            return repaired

    if primary.kind in ("type_mismatch", "failed_typeclass"):
        updated = _ensure_typed_binders(candidate)
        if updated != candidate:
            return updated
        ident = _infer_simple_ident(candidate)
        if ident and ident[0].islower():
            binder_type = _infer_binder_type(candidate, ident)
            return _add_binder(candidate, ident, binder_type)

    return candidate


def _normalize_policy_output(value: PolicyOutput | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [entry for entry in value if isinstance(entry, str)]


_UNKNOWN_IDENT_QUOTED_RE = re.compile(
    r"unknown (?:identifier|constant|declaration|name) ['`]([^'`\\s]+)['`]",
    re.IGNORECASE,
)
_UNKNOWN_IDENT_RE = re.compile(
    r"unknown (?:identifier|constant|declaration|name) ([A-Za-z_][\\w']*)",
    re.IGNORECASE,
)


def _extract_unknown_ident(message: str) -> str | None:
    quoted = _UNKNOWN_IDENT_QUOTED_RE.search(message)
    if quoted:
        return quoted.group(1)
    match = _UNKNOWN_IDENT_RE.search(message)
    if match:
        return match.group(1)
    return None


def _infer_simple_ident(candidate: str) -> str | None:
    colon_idx = _find_top_level_colon(candidate)
    if colon_idx == -1:
        return None
    type_expr = candidate[colon_idx + 1 :].strip()
    if re.fullmatch(r"[a-z][A-Za-z0-9_']*", type_expr):
        return type_expr
    return None


def _infer_binder_type(candidate: str, ident: str) -> str:
    colon_idx = _find_top_level_colon(candidate)
    if colon_idx == -1:
        return "Type"

    type_expr = candidate[colon_idx + 1 :].strip()
    if re.fullmatch(re.escape(ident), type_expr):
        return "Prop"

    prop_shaped = (
        rf"\b{re.escape(ident)}\b\s*->",
        rf"->\s*{re.escape(ident)}\b",
    )
    if any(re.search(pattern, type_expr) for pattern in prop_shaped):
        return "Prop"
    return "Type"


def _find_top_level_colon(candidate: str) -> int:
    depth = 0
    for idx, ch in enumerate(candidate):
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        elif ch == ":" and depth == 0:
            return idx
    return -1


def _add_binder(candidate: str, ident: str, binder_type: str = "Type") -> str:
    colon_idx = _find_top_level_colon(candidate)
    if colon_idx == -1:
        return candidate

    prefix = candidate[:colon_idx].rstrip()
    if re.search(rf"[({{]\s*{re.escape(ident)}\b", prefix):
        return candidate

    binder = f"({ident} : {binder_type})"
    return f"{prefix} {binder}{candidate[colon_idx:]}"


def _ensure_typed_binders(candidate: str) -> str:
    def _paren_repl(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        return f"({name} : Type)"

    def _brace_repl(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        return f"{{{name} : Type}}"

    updated = re.sub(r"\((\s*[A-Za-z_][\w']*)\s*\)", _paren_repl, candidate)
    updated = re.sub(r"\{(\s*[A-Za-z_][\w']*)\s*\}", _brace_repl, updated)
    return updated


def _fix_parse(candidate: str) -> str:
    header = candidate.splitlines()[0]
    if "--" in header:
        header = header.split("--", 1)[0].rstrip()

    colon_idx = _find_top_level_colon(header)
    if colon_idx == -1:
        return _truncate_unbalanced(header)

    prefix = header[: colon_idx + 1]
    type_expr = header[colon_idx + 1 :].strip()
    truncated = _truncate_unbalanced(type_expr)
    if truncated != type_expr:
        return f"{prefix} {truncated.strip()}"

    tokens = type_expr.split()
    if len(tokens) > 1:
        type_expr = tokens[0]

    return f"{prefix} {type_expr}"


def _repair_not_proposition(candidate: str) -> str:
    colon_idx = _find_top_level_colon(candidate)
    if colon_idx == -1:
        return candidate

    prefix = candidate[: colon_idx + 1]
    type_expr = candidate[colon_idx + 1 :].strip()
    if not type_expr:
        return f"{prefix} True"

    if re.fullmatch(r"[A-Za-z_][\w']*", type_expr):
        return f"{prefix} {type_expr} = {type_expr}"

    if "Type" in type_expr or "Sort" in type_expr:
        return f"{prefix} Nonempty ({type_expr})"

    return f"{prefix} True"


def _truncate_unbalanced(text: str) -> str:
    depth = 0
    last_balanced = None
    for idx, ch in enumerate(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                return text[:idx].rstrip()
            depth -= 1
        if depth == 0:
            last_balanced = idx

    if depth == 0:
        return text.rstrip()
    if last_balanced is None:
        return text.rstrip()
    return text[: last_balanced + 1].rstrip()


__all__ = ["Trace", "TraceStep", "default_policy", "repair_one"]
