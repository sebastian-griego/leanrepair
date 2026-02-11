from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Optional


@dataclass(frozen=True)
class ErrorInfo:
    message: str
    kind: str = "other"
    line: Optional[int] = None
    column: Optional[int] = None


_ERROR_RE = re.compile(r"^(.*?):(\d+):(\d+):\s*error:\s*(.*)$")

_UNKNOWN_PATTERNS = (
    "unknown identifier",
    "unknown constant",
    "unknown declaration",
    "unknown name",
)

_TYPE_MISMATCH_PATTERNS = (
    "type mismatch",
    "has type",
    "expected type",
    "type expected",
    "but is",
)

_NOT_PROPOSITION_PATTERNS = (
    "is not a proposition",
    "expected proposition",
)

_FAILED_TYPECLASS_PATTERNS = (
    "failed to synthesize",
    "typeclass",
    "failed to find instance",
    "could not synthesize",
)

_PARSE_PATTERNS = (
    "unexpected token",
    "unexpected end of input",
    "parse error",
    "expected token",
    "invalid syntax",
    "unterminated",
)

_NOTATION_PATTERNS = (
    "unknown notation",
    "unknown scoped notation",
    "invalid notation",
    "unknown scope",
    "failed to find notation",
)


def parse_errors(raw: str) -> List[ErrorInfo]:
    errors: List[ErrorInfo] = []
    for line in raw.splitlines():
        stripped = line.strip()
        match = _ERROR_RE.match(stripped)
        if match:
            _, line_no, col_no, message = match.groups()
            msg = message.strip()
            errors.append(
                ErrorInfo(
                    message=msg,
                    kind=_classify_error(msg),
                    line=int(line_no),
                    column=int(col_no),
                )
            )
            continue
        if "error:" in stripped:
            _, message = stripped.split("error:", 1)
            msg = message.strip()
            if msg:
                errors.append(ErrorInfo(message=msg, kind=_classify_error(msg)))
    return errors


def _classify_error(message: str) -> str:
    msg = message.lower()
    if _contains_any(msg, _UNKNOWN_PATTERNS):
        return "unknown_identifier"
    if _contains_any(msg, _NOT_PROPOSITION_PATTERNS):
        return "not_proposition"
    if _contains_any(msg, _FAILED_TYPECLASS_PATTERNS):
        return "failed_typeclass"
    if _contains_any(msg, _TYPE_MISMATCH_PATTERNS):
        return "type_mismatch"
    if _contains_any(msg, _NOTATION_PATTERNS):
        return "notation_scope"
    if _contains_any(msg, _PARSE_PATTERNS):
        return "parse_error"
    return "other"


def _contains_any(message: str, patterns: tuple[str, ...]) -> bool:
    return any(pat in message for pat in patterns)


__all__ = ["ErrorInfo", "parse_errors"]
