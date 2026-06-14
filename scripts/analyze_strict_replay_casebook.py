#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import strict_replay_analysis as sra  # noqa: E402
import strict_replay_casebook as srcb  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a focused casebook from LeanRepair strict replay records."
    )
    parser.add_argument(
        "--records-jsonl",
        default="",
        help="strict_replay_records.jsonl path. If omitted, use --root/strict_replay_records.jsonl or replay --root.",
    )
    parser.add_argument(
        "--root",
        default="",
        help="Run directory or root containing run_*/ directories.",
    )
    parser.add_argument(
        "--policies",
        nargs="+",
        default=["heuristic", "research"],
        help="Policies to replay when --records-jsonl is unavailable.",
    )
    parser.add_argument("--token-recall-floor", type=float, default=0.2)
    parser.add_argument("--max-cases", type=int, default=25)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--cases-jsonl", default="")
    args = parser.parse_args(argv)

    records_path = Path(args.records_jsonl) if args.records_jsonl else None
    root = Path(args.root) if args.root else None
    if records_path is None and root is not None:
        candidate = root / "strict_replay_records.jsonl"
        if candidate.exists():
            records_path = candidate

    if records_path is not None:
        records = srcb.load_records_jsonl(records_path)
        default_dir = records_path.parent
    elif root is not None:
        records = sra.replay_root(
            root,
            args.policies,
            token_recall_floor=float(args.token_recall_floor),
        )
        default_dir = root
    else:
        raise SystemExit("provide --records-jsonl or --root")

    summary = srcb.analyze_records(records, max_cases=int(args.max_cases))
    markdown = srcb.format_markdown(summary)

    output_json = (
        Path(args.output_json)
        if args.output_json
        else default_dir / "strict_replay_casebook.json"
    )
    output_md = (
        Path(args.output_md)
        if args.output_md
        else default_dir / "strict_replay_casebook.md"
    )
    cases_jsonl = (
        Path(args.cases_jsonl)
        if args.cases_jsonl
        else default_dir / "strict_replay_casebook_cases.jsonl"
    )

    output_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(markdown + "\n", encoding="utf-8")
    srcb.write_cases_jsonl(cases_jsonl, summary["focused_cases"])
    print(f"Wrote {output_json}, {output_md}, and {cases_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
