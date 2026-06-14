#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import trace_analysis as ta  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize LeanRepair traces by error kind, corruption, and repair outcome."
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
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    parser.add_argument("--output-md", default="", help="Optional output Markdown path.")
    parser.add_argument(
        "--max-examples",
        type=int,
        default=20,
        help="Maximum unsolved examples to keep per policy summary.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    summary = ta.analyze_root(
        root,
        args.policies,
        max_examples=int(args.max_examples),
    )
    markdown = ta.format_markdown(summary)

    output_json = Path(args.output_json) if args.output_json else root / "trace_taxonomy.json"
    output_md = Path(args.output_md) if args.output_md else root / "trace_taxonomy.md"
    output_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(markdown, encoding="utf-8")
    print(f"Wrote {output_json} and {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
