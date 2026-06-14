#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import strict_replay_analysis as sra  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay LeanRepair traces with degenerate accepted fixes filtered out."
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Run directory with policy JSONLs, or a root containing run_*/ directories.",
    )
    parser.add_argument(
        "--policies",
        nargs="+",
        default=["heuristic", "research"],
        help="Policy JSONL basenames to analyze.",
    )
    parser.add_argument("--token-recall-floor", type=float, default=0.2)
    parser.add_argument("--max-examples", type=int, default=20)
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    parser.add_argument("--output-md", default="", help="Optional output Markdown path.")
    parser.add_argument(
        "--output-records-jsonl",
        default="",
        help="Optional output JSONL path for per-record replay decisions.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    summary = sra.analyze_root(
        root,
        args.policies,
        token_recall_floor=float(args.token_recall_floor),
        max_examples=int(args.max_examples),
    )
    markdown = sra.format_markdown(summary)
    replay_rows = sra.replay_root(
        root,
        args.policies,
        token_recall_floor=float(args.token_recall_floor),
    )

    output_json = Path(args.output_json) if args.output_json else root / "strict_replay.json"
    output_md = Path(args.output_md) if args.output_md else root / "strict_replay.md"
    output_records = (
        Path(args.output_records_jsonl)
        if args.output_records_jsonl
        else root / "strict_replay_records.jsonl"
    )
    output_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(markdown + "\n", encoding="utf-8")
    sra.write_replay_records_jsonl(output_records, replay_rows)
    print(f"Wrote {output_json}, {output_md}, and {output_records}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
