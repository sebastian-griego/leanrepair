#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import budget_analysis as ba  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute LeanRepair solve/exact curves as a function of repair-step budget."
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
    parser.add_argument("--max-budget", type=int, default=0, help="0 = observed max steps")
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    parser.add_argument("--output-md", default="", help="Optional output Markdown path.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    summary = ba.analyze_root(
        root,
        args.policies,
        max_budget=int(args.max_budget) if int(args.max_budget) > 0 else None,
    )
    markdown = ba.format_markdown(summary)

    output_json = Path(args.output_json) if args.output_json else root / "budget_curve.json"
    output_md = Path(args.output_md) if args.output_md else root / "budget_curve.md"
    output_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    output_md.write_text(markdown + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {output_json} and {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
