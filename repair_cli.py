from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Add src directory to path for module imports
_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))

import acceptance
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
        "--policy",
        choices=("heuristic", "research", "research_strict", "openai"),
        default="heuristic",
        help="Policy backend",
    )

    args = parser.parse_args(argv)

    policy = _make_policy(args.policy)
    run_dataset(
        input_path=Path(args.input),
        output_path=Path(args.output),
        Tmax=args.Tmax,
        timeout_s=args.timeout_s,
        policy=policy,
        acceptance_rule=args.acceptance,
        token_recall_floor=args.token_recall_floor,
    )
    return 0


def run_dataset(
    input_path: Path,
    output_path: Path,
    Tmax: int,
    timeout_s: float,
    policy: LLMPolicy,
    acceptance_rule: str = "lean_ok",
    token_recall_floor: float = 0.2,
) -> None:
    policy_fn = lambda nl, ctx, cand, result: policy.propose_many(nl, ctx, cand, result)

    with input_path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        for line_no, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                record = {"id": str(line_no), "nl": "", "ctx": "", "candidate": ""}

            item_id = record.get("id", str(line_no))
            nl = record.get("nl", "") or ""
            ctx = record.get("ctx", "") or ""
            candidate = record.get("candidate", "") or ""
            target = record.get("target", "") or ""
            accept_fn = _make_acceptance(
                acceptance_rule,
                target=str(target),
                token_recall_floor=float(token_recall_floor),
            )

            trace = rl.repair_one(nl, ctx, candidate, Tmax, timeout_s, policy_fn, accept=accept_fn)
            output_record = _trace_to_record(item_id, trace, acceptance_rule=acceptance_rule)
            out.write(json.dumps(output_record, ensure_ascii=True) + "\n")


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
