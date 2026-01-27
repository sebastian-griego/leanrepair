from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
import re
import subprocess
import tempfile
import time
from typing import Optional, List

from lean_errors import ErrorInfo, parse_errors


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    errors: List[ErrorInfo]
    raw: str
    elapsed_ms: int
    timed_out: bool


_THEOREM_RE = re.compile(r"\b(theorem|lemma)\b", re.IGNORECASE)
_FORBIDDEN_RE = re.compile(
    r"\b(import|open|namespace|section|macro|syntax|set_option|attribute|inductive|structure|class|instance)\b|#eval|#reduce",
    re.IGNORECASE,
)

_CACHE: dict[str, CheckResult] = {}


def sanitize_candidate(text: str) -> Optional[str]:
    if not text or not text.strip():
        return None

    if "`" in text:
        return None

    if _FORBIDDEN_RE.search(text):
        return None

    matches = list(_THEOREM_RE.finditer(text))
    if len(matches) != 1:
        return None

    match = matches[0]
    if any(ch.strip() for ch in text[: match.start()]):
        return None

    body = text[match.start() :]
    if ":=" in body:
        body = body.split(":=", 1)[0]

    body = body.strip()
    if len(list(_THEOREM_RE.finditer(body))) != 1:
        return None

    return body


def build_theorem(sanitized: str) -> str:
    if not sanitized or not sanitized.strip():
        raise ValueError("sanitized theorem is empty")

    header = sanitized.strip()
    if ":=" in header:
        header = header.split(":=", 1)[0].rstrip()

    if len(_THEOREM_RE.findall(header)) != 1:
        raise ValueError("expected a single theorem or lemma header")

    if not header.lower().lstrip().startswith(("theorem", "lemma")):
        raise ValueError("header must start with theorem or lemma")

    return f"{header} := by sorry"


def lean_check(context: str, theorem: str, timeout_s: float) -> CheckResult:
    context = context or ""
    theorem = theorem or ""
    file_contents = (context.rstrip() + "\n\n" + theorem.strip() + "\n").lstrip()
    key = hashlib.sha256(file_contents.encode("utf-8")).hexdigest()
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    raw, elapsed_ms, timed_out, exit_code = _run_lean(file_contents, timeout_s)
    logger.debug("Lean output:\n%s", raw)

    errors = parse_errors(raw)
    if timed_out:
        if not errors:
            errors = [ErrorInfo("Lean check timed out")]
        result = CheckResult(False, errors, raw, elapsed_ms, True)
    else:
        ok = (exit_code == 0) and not errors
        if exit_code not in (0, None) and not errors:
            errors = [ErrorInfo("Lean check failed")]
        result = CheckResult(ok, errors, raw, elapsed_ms, False)

    _CACHE[key] = result
    return result


def _run_lean(file_contents: str, timeout_s: float) -> tuple[str, int, bool, Optional[int]]:
    start = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="leancheck_") as tmpdir:
            path = f"{tmpdir}/Main.lean"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(file_contents)
            try:
                proc = subprocess.run(
                    ["lake", "env", "lean", path],
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                raw = (proc.stdout or "") + (proc.stderr or "")
                return raw, _elapsed_ms(start), False, proc.returncode
            except subprocess.TimeoutExpired as exc:
                raw = (exc.stdout or "") + (exc.stderr or "")
                return raw, _elapsed_ms(start), True, None
    except FileNotFoundError as exc:
        raw = str(exc)
        return raw, _elapsed_ms(start), False, None


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


__all__ = [
    "CheckResult",
    "ErrorInfo",
    "sanitize_candidate",
    "build_theorem",
    "lean_check",
]
