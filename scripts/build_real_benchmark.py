#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import lean_check as lc  # noqa: E402


CorruptFn = Callable[[str, random.Random], str]

THEOREM_LINE_RE = re.compile(r"^\s*(theorem|lemma)\s+([^\s:]+)\s*(.*)$")
HEADER_NAME_RE = re.compile(r"^\s*(theorem|lemma)\s+([^\s:]+)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build real-data Lean repair benchmark from Lean source files.")
    parser.add_argument("--output", default="data/real_benchmark.jsonl", help="Output JSONL path")
    parser.add_argument("--num-items", type=int, default=300, help="Target number of benchmark items")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument(
        "--lean-src-root",
        default=str(Path.home() / ".elan/toolchains/leanprover--lean4---v4.21.0/src/lean"),
        help="Root directory containing Lean source modules",
    )
    parser.add_argument(
        "--subdirs",
        nargs="+",
        default=["Init", "Std"],
        help="Subdirectories inside lean-src-root to mine",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=25.0,
        help="Timeout for Lean validation checks",
    )
    parser.add_argument(
        "--min-candidates",
        type=int,
        default=800,
        help="Minimum extracted raw headers before filtering",
    )
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lean_root = Path(args.lean_src_root).resolve()
    if not lean_root.exists():
        raise SystemExit(f"Lean source root not found: {lean_root}")

    raw_candidates = _extract_headers(lean_root, args.subdirs)
    if len(raw_candidates) < args.min_candidates:
        raise SystemExit(
            f"Too few extracted headers ({len(raw_candidates)}); expected at least {args.min_candidates}. "
            "Try adjusting --subdirs or --lean-src-root."
        )

    rng.shuffle(raw_candidates)
    corruptions: list[tuple[str, CorruptFn]] = [
        ("unknown_type_symbol", _corrupt_unknown_type_symbol),
        ("lowercase_type", _corrupt_lowercase_type),
        ("parse_missing_colon", _corrupt_parse_missing_colon),
        ("parse_unbalanced_paren", _corrupt_parse_unbalanced_paren),
        ("not_proposition", _corrupt_not_proposition),
        ("type_mismatch", _corrupt_type_mismatch),
    ]

    records: list[dict[str, str]] = []
    seen_targets: set[str] = set()
    attempts = 0
    max_attempts = max(args.num_items * 60, 5000)

    while len(records) < args.num_items and attempts < max_attempts and raw_candidates:
        source = raw_candidates[attempts % len(raw_candidates)]
        attempts += 1

        target = _rename_decl(source["header"], f"bench_real_{len(records):05d}")
        target = lc.sanitize_candidate(target) or ""
        if not target or target in seen_targets:
            continue

        context = f"import {source['module']}\n"

        target_result = lc.lean_check(context, lc.build_theorem(target), args.timeout_s)
        if not target_result.ok:
            continue

        corruption_name, corruption_fn = rng.choice(corruptions)
        candidate = corruption_fn(target, rng)
        candidate = lc.sanitize_candidate(candidate) or ""
        if not candidate or candidate == target:
            continue

        cand_result = lc.lean_check(context, lc.build_theorem(candidate), args.timeout_s)
        if cand_result.ok:
            continue

        seen_targets.add(target)
        records.append(
            {
                "id": f"real_{len(records):05d}",
                "nl": f"Repair theorem header mined from Lean {source['module']}",
                "ctx": context,
                "candidate": candidate,
                "target": target,
                "corruption": corruption_name,
                "source_module": source["module"],
                "source_file": source["file"],
                "source_line": str(source["line"]),
            }
        )

    with output_path.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    print(f"extracted={len(raw_candidates)} selected={len(records)} attempts={attempts} output={output_path}")
    return 0


def _extract_headers(lean_root: Path, subdirs: list[str]) -> list[dict[str, str | int]]:
    headers: list[dict[str, str | int]] = []
    for subdir in subdirs:
        base = (lean_root / subdir).resolve()
        if not base.exists():
            continue
        for path in base.rglob("*.lean"):
            module = _module_from_path(lean_root, path)
            if not module:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                candidate = _extract_header_from_line(line)
                if not candidate:
                    continue
                sanitized = lc.sanitize_candidate(candidate)
                if sanitized is None:
                    continue
                headers.append(
                    {
                        "module": module,
                        "header": sanitized,
                        "file": str(path),
                        "line": line_no,
                    }
                )
    return headers


def _module_from_path(lean_root: Path, path: Path) -> str:
    try:
        rel = path.resolve().relative_to(lean_root)
    except ValueError:
        return ""
    if rel.suffix != ".lean":
        return ""
    return ".".join(rel.with_suffix("").parts)


def _extract_header_from_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("--"):
        return None
    if " where" in stripped:
        return None
    match = THEOREM_LINE_RE.match(stripped)
    if not match:
        return None
    if ":" not in stripped:
        return None
    if stripped.endswith(":"):
        return None
    header = stripped.split(":=", 1)[0].strip()
    # Skip malformed theorem names containing delimiters; these are usually macro-heavy forms.
    name_match = HEADER_NAME_RE.match(header)
    if not name_match:
        return None
    name = name_match.group(2)
    if any(ch in name for ch in "(){}[]"):
        return None
    return header


def _rename_decl(header: str, new_name: str) -> str:
    match = HEADER_NAME_RE.match(header)
    if not match:
        return header
    kind = match.group(1)
    old_name = match.group(2)
    return re.sub(
        rf"^\s*{re.escape(kind)}\s+{re.escape(old_name)}\b",
        f"{kind} {new_name}",
        header,
        count=1,
    )


def _corrupt_unknown_type_symbol(target: str, rng: random.Random) -> str:
    candidates = [source for source in ("List Nat", "Nat", "Bool", "Prop", "Int") if source in target]
    if candidates:
        return target.replace(rng.choice(candidates), "Foo", 1)
    return target


def _corrupt_lowercase_type(target: str, rng: random.Random) -> str:
    replacements = (
        ("List Nat", "list nat"),
        ("Nat", "nat"),
        ("Bool", "bool"),
        ("Prop", "prop"),
        ("Int", "int"),
        ("String", "string"),
    )
    candidates = [(src, dst) for src, dst in replacements if src in target]
    if candidates:
        src, dst = rng.choice(candidates)
        return target.replace(src, dst, 1)
    return target


def _corrupt_parse_missing_colon(target: str, rng: random.Random) -> str:
    del rng
    colon = _find_top_level_colon(target)
    if colon == -1:
        return target
    return f"{target[:colon]} {target[colon + 1:]}"


def _corrupt_parse_unbalanced_paren(target: str, rng: random.Random) -> str:
    indices = [idx for idx, ch in enumerate(target) if ch == ")"]
    if not indices:
        return target
    idx = rng.choice(indices)
    return target[:idx] + target[idx + 1 :]


def _corrupt_not_proposition(target: str, rng: random.Random) -> str:
    colon = _find_top_level_colon(target)
    if colon == -1:
        return target
    binders = _binder_names(target[:colon])
    chosen = rng.choice(binders) if binders else "Nat"
    return f"{target[: colon + 1]} {chosen}"


def _corrupt_type_mismatch(target: str, rng: random.Random) -> str:
    colon = _find_top_level_colon(target)
    if colon == -1:
        return target
    goal = target[colon + 1 :].strip()
    if "=" in goal:
        left, _ = goal.split("=", 1)
        rhs = rng.choice(["True", "False", "0"])
        return f"{target[: colon + 1]} {left.strip()} = {rhs}"
    if "->" in goal:
        left, _ = goal.rsplit("->", 1)
        rhs = rng.choice(["Nat", "Bool"])
        return f"{target[: colon + 1]} {left.strip()} -> {rhs}"
    return f"{target[: colon + 1]} Nat = True"


def _find_top_level_colon(candidate: str) -> int:
    depth = 0
    for idx, ch in enumerate(candidate):
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        elif ch == ":" and depth == 0:
            return idx
    return -1


def _binder_names(prefix: str) -> list[str]:
    out: list[str] = []
    for match in re.finditer(r"\(([^)]*)\)", prefix):
        body = match.group(1)
        if ":" not in body:
            continue
        names_part, _ = body.split(":", 1)
        for token in names_part.split():
            name = token.strip()
            if re.fullmatch(r"[A-Za-z_][\w']*", name):
                out.append(name)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
