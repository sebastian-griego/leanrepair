from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Callable, List

import lean_check as lc
from lean_errors import ErrorInfo


@dataclass(frozen=True)
class TraceStep:
    candidate: str
    result: lc.CheckResult


@dataclass
class Trace:
    steps: List[TraceStep] = field(default_factory=list)


PolicyFn = Callable[[str, str, str, lc.CheckResult], str]


def repair_one(
    nl: str,
    ctx: str,
    candidate0: str,
    Tmax: int,
    timeout_s: float,
    policy: PolicyFn,
) -> Trace:
    trace = Trace()
    seen: set[str] = set()
    current = candidate0 or ""

    if Tmax <= 0:
        return trace

    for _ in range(Tmax):
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
            break

        theorem = lc.build_theorem(sanitized)
        if theorem in seen:
            break
        seen.add(theorem)

        result = lc.lean_check(ctx, theorem, timeout_s)
        trace.steps.append(TraceStep(candidate=theorem, result=result))

        if result.ok:
            break

        current = policy(nl, ctx, sanitized, result)

    return trace


def default_policy(nl: str, ctx: str, candidate: str, result: lc.CheckResult) -> str:
    del nl, ctx

    if not result.errors:
        return candidate

    primary = result.errors[0]
    if primary.kind == "unknown_identifier":
        ident = _extract_unknown_ident(primary.message) or _infer_simple_ident(candidate)
        if ident and ident[0].islower():
            return _add_binder(candidate, ident)

    if primary.kind == "parse_error":
        return _fix_parse(candidate)

    if primary.kind in ("type_mismatch", "failed_typeclass"):
        updated = _ensure_typed_binders(candidate)
        if updated != candidate:
            return updated
        ident = _infer_simple_ident(candidate)
        if ident and ident[0].islower():
            return _add_binder(candidate, ident)

    return candidate


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


def _add_binder(candidate: str, ident: str) -> str:
    colon_idx = _find_top_level_colon(candidate)
    if colon_idx == -1:
        return candidate

    prefix = candidate[:colon_idx].rstrip()
    if re.search(rf"[({{]\s*{re.escape(ident)}\b", prefix):
        return candidate

    binder = f"({ident} : Type)"
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
