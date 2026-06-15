#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from artifact_manifest import ManifestError, verify_manifest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify LeanRepair run-directory artifact manifests."
    )
    parser.add_argument(
        "--run-dir",
        action="append",
        default=[],
        help="Run directory containing manifest.json. May be repeated.",
    )
    parser.add_argument(
        "--root",
        default="",
        help="Directory whose child run_*/ directories should be verified.",
    )
    parser.add_argument(
        "--allow-extra",
        action="store_true",
        help="Allow files that are not listed in manifest.json.",
    )
    args = parser.parse_args(argv)

    run_dirs = [Path(value) for value in args.run_dir]
    if args.root:
        root = Path(args.root)
        run_dirs.extend(
            sorted(
                path
                for path in root.iterdir()
                if path.is_dir() and path.name.startswith("run_")
            )
        )
    if not run_dirs:
        parser.error("provide --run-dir or --root")

    verified = []
    for run_dir in run_dirs:
        try:
            manifest = verify_manifest(run_dir, allow_extra=bool(args.allow_extra))
        except ManifestError as exc:
            print(f"manifest error in {run_dir}: {exc}", file=sys.stderr)
            return 1
        row = {
            "run_dir": str(run_dir).replace("\\", "/"),
            "artifact_count": int(manifest["artifact_count"]),
        }
        if manifest.get("run_id"):
            row["run_id"] = str(manifest["run_id"])
        verified.append(row)

    print(json.dumps({"verified": verified}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
