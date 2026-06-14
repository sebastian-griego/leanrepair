#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import eval_utils as eu  # noqa: E402
import acceptance  # noqa: E402
import budget_analysis as ba  # noqa: E402
import exactness_analysis as ea  # noqa: E402
from jsonl_io import JsonlError, iter_jsonl_objects  # noqa: E402
import lean_check as lc  # noqa: E402
import quality_analysis as qa  # noqa: E402
import repair_cli as rc  # noqa: E402
import repair_loop as rl  # noqa: E402
import semantic_drift_analysis as sda  # noqa: E402
import strict_replay_analysis as sra  # noqa: E402
import strict_replay_casebook as srcb  # noqa: E402
import strict_replay_paired as srp  # noqa: E402
import trace_analysis as ta  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Lean repair experiments and summarize results.")
    parser.add_argument("--input", required=True, help="Input benchmark JSONL")
    parser.add_argument("--output-dir", default="results", help="Directory to write outputs")
    parser.add_argument(
        "--policies",
        nargs="+",
        default=["heuristic", "research"],
        choices=("heuristic", "research", "research_strict", "openai"),
        help="Policies to evaluate",
    )
    parser.add_argument("--Tmax", type=int, default=6, help="Maximum repair steps per item")
    parser.add_argument("--timeout-s", type=float, default=20.0, help="Lean timeout per check")
    parser.add_argument(
        "--acceptance",
        choices=("lean_ok", "strict"),
        default="lean_ok",
        help="Acceptance rule for Lean-ok candidates.",
    )
    parser.add_argument("--token-recall-floor", type=float, default=0.2)
    parser.add_argument("--warmup", action="store_true", help="Run one warmup Lean check before evaluation")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    dataset = _load_benchmark(input_path)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.output_dir) / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.warmup:
        _warmup(args.timeout_s)

    aggregate_summary: dict[str, Any] = {
        "input": str(input_path),
        "count": len(dataset),
        "created_at_utc": timestamp,
        "Tmax": args.Tmax,
        "timeout_s": args.timeout_s,
        "acceptance": args.acceptance,
        "token_recall_floor": args.token_recall_floor,
        "policies": {},
    }

    for policy_name in args.policies:
        policy = rc._make_policy(policy_name)
        result_path = run_dir / f"{policy_name}.jsonl"
        records = _run_policy(
            dataset,
            policy_name,
            policy,
            args.Tmax,
            args.timeout_s,
            result_path,
            acceptance_rule=args.acceptance,
            token_recall_floor=float(args.token_recall_floor),
        )
        summary = eu.summarize(records)
        aggregate_summary["policies"][policy_name] = summary
        with (run_dir / f"{policy_name}.summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=True)

    with (run_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(aggregate_summary, handle, indent=2, ensure_ascii=True)
    _write_markdown_report(run_dir / "report.md", aggregate_summary)
    _write_trace_taxonomy(run_dir, args.policies)
    _write_budget_curve(run_dir, args.policies)
    _write_exactness_gap(run_dir, args.policies)
    _write_semantic_drift(run_dir, args.policies)
    _write_quality_summary(run_dir, args.policies)
    _write_strict_replay(run_dir, args.policies)

    print(f"Wrote experiment outputs to {run_dir}")
    return 0


def _run_policy(
    dataset: list[dict[str, Any]],
    policy_name: str,
    policy: object,
    Tmax: int,
    timeout_s: float,
    output_path: Path,
    *,
    acceptance_rule: str = "lean_ok",
    token_recall_floor: float = 0.2,
) -> list[eu.ExperimentRecord]:
    records: list[eu.ExperimentRecord] = []
    policy_fn = lambda nl, ctx, cand, result: policy.propose_many(nl, ctx, cand, result)

    with output_path.open("w", encoding="utf-8") as out:
        for item in dataset:
            item_id = str(item.get("id", ""))
            nl = str(item.get("nl", "") or "")
            ctx = str(item.get("ctx", "") or "")
            candidate = str(item.get("candidate", "") or "")
            target = str(item.get("target", "") or "")
            corruption = str(item.get("corruption", "unknown") or "unknown")
            accept_fn = _make_acceptance(
                acceptance_rule,
                target=target,
                token_recall_floor=token_recall_floor,
            )

            trace = rl.repair_one(
                nl=nl,
                ctx=ctx,
                candidate0=candidate,
                Tmax=Tmax,
                timeout_s=timeout_s,
                policy=policy_fn,
                accept=accept_fn,
            )

            final_step = trace.final_step
            final = final_step.candidate if final_step else ""
            ok = trace.accepted
            elapsed_ms = sum(step.result.elapsed_ms for step in trace.steps)

            records.append(
                eu.ExperimentRecord(
                    item_id=item_id,
                    policy=policy_name,
                    corruption=corruption,
                    ok=ok,
                    steps=len(trace.steps),
                    elapsed_ms=elapsed_ms,
                    final=final,
                    target=target,
                )
            )

            out_record = {
                "id": item_id,
                "policy": policy_name,
                "corruption": corruption,
                "ok": ok,
                "acceptance": acceptance_rule,
                "steps": len(trace.steps),
                "elapsed_ms": elapsed_ms,
                "candidate0": candidate,
                "target": target,
                "final": final,
                "final_header": eu.normalize_header(final),
                "target_header": eu.normalize_header(target),
                "exact": ok and eu.normalize_header(final) == eu.normalize_header(target),
                "trace": [_trace_step_to_dict(step) for step in trace.steps],
            }
            out.write(json.dumps(out_record, ensure_ascii=True) + "\n")

    return records


def _trace_step_to_dict(step: rl.TraceStep) -> dict[str, Any]:
    return {
        "candidate": step.candidate,
        "ok": step.result.ok,
        "accepted": step.accepted,
        "acceptance_reason": step.acceptance_reason,
        "errors": [
            {
                "kind": err.kind,
                "message": err.message,
                "line": err.line,
                "column": err.column,
            }
            for err in step.result.errors
        ],
        "elapsed_ms": step.result.elapsed_ms,
        "timed_out": step.result.timed_out,
        "raw": step.result.raw,
    }


def _load_benchmark(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, row in iter_jsonl_objects(path):
        _validate_benchmark_row(row, path=path, line_no=line_no)
        rows.append(row)
    if not rows:
        raise JsonlError(f"Empty benchmark at {path}")
    return rows


def _validate_benchmark_row(row: dict[str, Any], *, path: Path, line_no: int) -> None:
    for key in ("id", "candidate", "target"):
        value = row.get(key)
        if not isinstance(value, str) or not value.strip():
            raise JsonlError(
                f"Expected non-empty string field {key!r} at {path}:{line_no}"
            )
    for key in ("nl", "ctx", "corruption"):
        value = row.get(key)
        if value is not None and not isinstance(value, str):
            raise JsonlError(
                f"Expected string field {key!r} at {path}:{line_no}, got {type(value).__name__}"
            )


def _warmup(timeout_s: float) -> None:
    lc._CACHE.clear()
    lc.lean_check("", "theorem warmup : True := by sorry", max(timeout_s, 20.0))


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


def _write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# LeanRepair Experiment Report",
        "",
        f"- Input: `{summary['input']}`",
        f"- Dataset size: `{summary['count']}`",
        f"- Tmax: `{summary['Tmax']}`",
        f"- Timeout (s): `{summary['timeout_s']}`",
        f"- Acceptance: `{summary.get('acceptance', 'lean_ok')}`",
        f"- Created (UTC): `{summary['created_at_utc']}`",
        "",
        "## Policy Summary",
        "",
        "| Policy | Solve Rate | 95% CI | Exact Rate | Avg Steps | Avg Elapsed (ms) |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    policies = summary.get("policies", {})
    for name in sorted(policies):
        row = policies[name]
        solve_lo, solve_hi = row["solve_rate_ci95"]
        lines.append(
            "| "
            + name
            + " | "
            + f"{100.0 * row['solve_rate']:.1f}%"
            + " | "
            + f"[{100.0 * solve_lo:.1f}, {100.0 * solve_hi:.1f}]%"
            + " | "
            + f"{100.0 * row['exact_rate']:.1f}%"
            + " | "
            + f"{row['avg_steps']:.2f}"
            + " | "
            + f"{row['avg_elapsed_ms']:.1f}"
            + " |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_trace_taxonomy(run_dir: Path, policies: list[str]) -> None:
    summary = ta.analyze_run_dir(run_dir, policies, max_examples=20)
    (run_dir / "trace_taxonomy.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "trace_taxonomy.md").write_text(
        ta.format_markdown(summary),
        encoding="utf-8",
    )


def _write_budget_curve(run_dir: Path, policies: list[str]) -> None:
    summary = ba.analyze_root(run_dir, policies)
    (run_dir / "budget_curve.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "budget_curve.md").write_text(
        ba.format_markdown(summary) + "\n",
        encoding="utf-8",
    )


def _write_exactness_gap(run_dir: Path, policies: list[str]) -> None:
    summary = ea.analyze_run_dir(run_dir, policies, max_examples=20)
    (run_dir / "exactness_gap.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "exactness_gap.md").write_text(
        ea.format_markdown(summary) + "\n",
        encoding="utf-8",
    )


def _write_semantic_drift(run_dir: Path, policies: list[str]) -> None:
    summary = sda.analyze_run_dir(run_dir, policies, max_examples=20)
    (run_dir / "semantic_drift.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "semantic_drift.md").write_text(
        sda.format_markdown(summary) + "\n",
        encoding="utf-8",
    )


def _write_quality_summary(run_dir: Path, policies: list[str]) -> None:
    summary = qa.analyze_root(run_dir, policies)
    (run_dir / "quality_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "quality_summary.md").write_text(
        qa.format_markdown(summary) + "\n",
        encoding="utf-8",
    )


def _write_strict_replay(run_dir: Path, policies: list[str]) -> None:
    summary = sra.analyze_run_dir(run_dir, policies, max_examples=20)
    replay_rows = sra.replay_run_dir(run_dir, policies)
    casebook = srcb.analyze_records(replay_rows, max_cases=25)
    (run_dir / "strict_replay.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "strict_replay.md").write_text(
        sra.format_markdown(summary) + "\n",
        encoding="utf-8",
    )
    sra.write_replay_records_jsonl(run_dir / "strict_replay_records.jsonl", replay_rows)
    (run_dir / "strict_replay_casebook.json").write_text(
        json.dumps(casebook, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "strict_replay_casebook.md").write_text(
        srcb.format_markdown(casebook) + "\n",
        encoding="utf-8",
    )
    srcb.write_cases_jsonl(run_dir / "strict_replay_casebook_cases.jsonl", casebook["focused_cases"])
    if len(policies) >= 2:
        paired = srp.analyze_records(
            replay_rows,
            policy_a=policies[0],
            policy_b=policies[1],
            max_cases=25,
        )
        (run_dir / "strict_replay_paired.json").write_text(
            json.dumps(paired, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        (run_dir / "strict_replay_paired.md").write_text(
            srp.format_markdown(paired) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    raise SystemExit(main())
