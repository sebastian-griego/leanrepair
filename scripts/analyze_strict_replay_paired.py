#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import strict_replay_analysis as sra  # noqa: E402
import strict_replay_paired as srp  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Paired policy comparison over strict replay decisions."
    )
    parser.add_argument(
        "--records-jsonl",
        default="",
        help="strict_replay_records.jsonl path. If omitted, replay --root.",
    )
    parser.add_argument(
        "--root",
        default="",
        help="Run directory with policy JSONLs, or a root containing run_*/ directories.",
    )
    parser.add_argument("--policy-a", default="heuristic", help="Baseline policy name.")
    parser.add_argument("--policy-b", default="research", help="Compared policy name.")
    parser.add_argument("--token-recall-floor", type=float, default=0.2)
    parser.add_argument("--strict-pairs", action="store_true")
    parser.add_argument("--max-cases", type=int, default=25)
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    parser.add_argument("--output-md", default="", help="Optional output Markdown path.")
    args = parser.parse_args(argv)

    records_path = Path(args.records_jsonl) if args.records_jsonl else None
    root = Path(args.root) if args.root else None
    if records_path is not None:
        records = srp.load_records_jsonl(records_path)
        default_dir = records_path.parent
    elif root is not None:
        records = sra.replay_root(
            root,
            [str(args.policy_a), str(args.policy_b)],
            token_recall_floor=float(args.token_recall_floor),
        )
        default_dir = root
    else:
        raise SystemExit("provide --records-jsonl or --root")

    summary = srp.analyze_records(
        records,
        policy_a=str(args.policy_a),
        policy_b=str(args.policy_b),
        strict_pairs=bool(args.strict_pairs),
        max_cases=int(args.max_cases),
    )
    markdown = srp.format_markdown(summary)

    output_json = (
        Path(args.output_json) if args.output_json else default_dir / "strict_replay_paired.json"
    )
    output_md = (
        Path(args.output_md) if args.output_md else default_dir / "strict_replay_paired.md"
    )
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
