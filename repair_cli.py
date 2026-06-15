from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

# Add src directory to path for module imports
_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))

import acceptance
from jsonl_io import JsonlError
import repair_loop as rl
from llm_policy import HeuristicPolicy, OpenAIChatPolicy, ResearchHeuristicPolicy, LLMPolicy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Lean repair loop over a JSONL dataset.")
    parser.add_argument("--input", required=True, help="Path to input JSONL")
    parser.add_argument("--output", required=True, help="Path to output JSONL")
    parser.add_argument("--Tmax", type=int, default=3, help="Maximum repair steps per item")
    parser.add_argument("--timeout-s", type=float, default=20.0, help="Lean check timeout in seconds")
    parser.add_argument(
        "--acceptance",
        choices=("lean_ok", "strict"),
        default="lean_ok",
        help="Acceptance rule for Lean-ok candidates.",
    )
    parser.add_argument("--token-recall-floor", type=float, default=0.2)
    parser.add_argument(
        "--skip-invalid-rows",
        action="store_true",
        help="skip malformed JSONL rows instead of failing before writing output",
    )
    parser.add_argument(
        "--policy",
        choices=("heuristic", "research", "research_strict", "openai"),
        default="heuristic",
        help="Policy backend",
    )

    args = parser.parse_args(argv)

    policy = _make_policy(args.policy)
    try:
        run_dataset(
            input_path=Path(args.input),
            output_path=Path(args.output),
            Tmax=args.Tmax,
            timeout_s=args.timeout_s,
            policy=policy,
            acceptance_rule=args.acceptance,
            token_recall_floor=args.token_recall_floor,
            skip_invalid_rows=args.skip_invalid_rows,
        )
    except JsonlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def run_dataset(
    input_path: Path,
    output_path: Path,
    Tmax: int,
    timeout_s: float,
    policy: LLMPolicy,
    acceptance_rule: str = "lean_ok",
    token_recall_floor: float = 0.2,
    skip_invalid_rows: bool = False,
) -> None:
    _validate_run_options(
        Tmax=Tmax,
        timeout_s=timeout_s,
        token_recall_floor=token_recall_floor,
    )
    records = _iter_input_records(input_path, skip_invalid_rows=skip_invalid_rows)
    _validate_input_records(
        records,
        input_path=input_path,
        require_target=acceptance_rule == "strict",
    )

    policy_fn = lambda nl, ctx, cand, result: policy.propose_many(nl, ctx, cand, result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as out:
        for _line_no, record in records:
            item_id = record["id"]
            nl = record.get("nl", "") or ""
            ctx = record.get("ctx", "") or ""
            candidate = record["candidate"]
            target = record.get("target", "") or ""
            accept_fn = _make_acceptance(
                acceptance_rule,
                target=str(target),
                token_recall_floor=float(token_recall_floor),
            )

            trace = rl.repair_one(nl, ctx, candidate, Tmax, timeout_s, policy_fn, accept=accept_fn)
            output_record = _trace_to_record(item_id, trace, acceptance_rule=acceptance_rule)
            out.write(json.dumps(output_record, ensure_ascii=True) + "\n")


def _iter_input_records(
    input_path: Path,
    *,
    skip_invalid_rows: bool = False,
) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                if skip_invalid_rows:
                    continue
                raise JsonlError(f"Invalid JSON at {input_path}:{line_no}: {exc.msg}") from exc
            if not isinstance(record, dict):
                if skip_invalid_rows:
                    continue
                raise JsonlError(
                    f"Expected JSON object at {input_path}:{line_no}, got {type(record).__name__}"
                )
            records.append((line_no, record))
    return records


def _validate_run_options(
    *,
    Tmax: int,
    timeout_s: float,
    token_recall_floor: float,
) -> None:
    if Tmax < 1:
        raise JsonlError(f"Tmax must be a positive integer, got {Tmax!r}")
    if timeout_s <= 0:
        raise JsonlError(f"timeout_s must be positive, got {timeout_s!r}")
    if not 0.0 <= token_recall_floor <= 1.0:
        raise JsonlError(
            f"token_recall_floor must be between 0 and 1, got {token_recall_floor!r}"
        )


def _validate_input_records(
    records: list[tuple[int, dict[str, Any]]],
    *,
    input_path: Path,
    require_target: bool = False,
) -> None:
    if not records:
        raise JsonlError(f"Empty input dataset at {input_path}")

    first_lines: dict[str, int] = {}
    for line_no, record in records:
        item_id = _require_nonempty_string_field(
            record,
            "id",
            input_path=input_path,
            line_no=line_no,
        )
        if item_id in first_lines:
            raise JsonlError(
                f"duplicate id {item_id!r} at {input_path}:{line_no}; "
                f"first seen at line {first_lines[item_id]}"
            )
        first_lines[item_id] = line_no

        _require_nonempty_string_field(
            record,
            "candidate",
            input_path=input_path,
            line_no=line_no,
        )
        if require_target:
            _require_nonempty_string_field(
                record,
                "target",
                input_path=input_path,
                line_no=line_no,
            )
        else:
            _validate_optional_string_field(
                record,
                "target",
                input_path=input_path,
                line_no=line_no,
            )
        _validate_optional_string_field(
            record,
            "nl",
            input_path=input_path,
            line_no=line_no,
        )
        _validate_optional_string_field(
            record,
            "ctx",
            input_path=input_path,
            line_no=line_no,
        )


def _require_nonempty_string_field(
    record: dict[str, Any],
    field: str,
    *,
    input_path: Path,
    line_no: int,
) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise JsonlError(
            f"Expected non-empty string field {field!r} at {input_path}:{line_no}, "
            f"got {type(value).__name__}"
        )
    return value


def _validate_optional_string_field(
    record: dict[str, Any],
    field: str,
    *,
    input_path: Path,
    line_no: int,
) -> None:
    value = record.get(field)
    if value is not None and not isinstance(value, str):
        raise JsonlError(
            f"Expected string field {field!r} at {input_path}:{line_no}, "
            f"got {type(value).__name__}"
        )


def _make_policy(kind: str) -> LLMPolicy:
    if kind == "openai":
        return OpenAIChatPolicy(fallback=HeuristicPolicy())
    if kind == "research_strict":
        return ResearchHeuristicPolicy(allow_degenerate_fallbacks=False)
    if kind == "research":
        return ResearchHeuristicPolicy()
    return HeuristicPolicy()


def _make_acceptance(
    kind: str,
    *,
    target: str,
    token_recall_floor: float = 0.2,
) -> rl.AcceptanceFn:
    if kind == "strict":
        return acceptance.strict_acceptance_for_target(
            target,
            token_recall_floor=token_recall_floor,
        )
    return acceptance.accept_lean_ok


def _trace_to_record(item_id: object, trace: rl.Trace, *, acceptance_rule: str = "lean_ok") -> dict:
    steps = len(trace.steps)
    final_step = trace.final_step
    final = final_step.candidate if final_step else ""
    ok = trace.accepted

    return {
        "id": item_id,
        "ok": ok,
        "acceptance": acceptance_rule,
        "final": final,
        "steps": steps,
        "trace": [_step_to_dict(step) for step in trace.steps],
    }


def _step_to_dict(step: rl.TraceStep) -> dict:
    result = step.result
    return {
        "candidate": step.candidate,
        "ok": result.ok,
        "accepted": step.accepted,
        "acceptance_reason": step.acceptance_reason,
        "errors": [
            {
                "message": err.message,
                "kind": err.kind,
                "line": err.line,
                "column": err.column,
            }
            for err in result.errors
        ],
        "raw": result.raw,
        "elapsed_ms": result.elapsed_ms,
        "timed_out": result.timed_out,
    }


if __name__ == "__main__":
    raise SystemExit(main())
