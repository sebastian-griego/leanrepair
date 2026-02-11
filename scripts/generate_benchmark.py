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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic Lean repair benchmark JSONL.")
    parser.add_argument("--output", default="data/synth_benchmark.jsonl", help="Output JSONL path")
    parser.add_argument("--num-items", type=int, default=300, help="Number of benchmark items")
    parser.add_argument("--seed", type=int, default=7, help="RNG seed")
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    corruption_ops: list[tuple[str, CorruptFn]] = [
        ("unknown_type_symbol", _corrupt_unknown_type_symbol),
        ("lowercase_type", _corrupt_lowercase_type),
        ("parse_missing_colon", _corrupt_parse_missing_colon),
        ("parse_unbalanced_paren", _corrupt_parse_unbalanced_paren),
        ("not_proposition", _corrupt_not_proposition),
        ("type_mismatch", _corrupt_type_mismatch),
    ]

    records: list[dict[str, str]] = []
    attempt = 0
    while len(records) < args.num_items and attempt < args.num_items * 20:
        idx = len(records)
        target = _make_target(idx, rng)
        corruption_name, corruption_fn = rng.choice(corruption_ops)
        candidate = corruption_fn(target, rng)

        if lc.sanitize_candidate(candidate) is None:
            attempt += 1
            continue
        if candidate.strip() == target.strip():
            attempt += 1
            continue

        records.append(
            {
                "id": f"synth_{idx:04d}",
                "nl": f"Repair Lean theorem header corrupted via {corruption_name}",
                "ctx": "",
                "candidate": candidate,
                "target": target,
                "corruption": corruption_name,
            }
        )
        attempt += 1

    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    print(f"Wrote {len(records)} items to {output_path}")
    return 0


def _make_target(i: int, rng: random.Random) -> str:
    builders = (
        lambda j: f"theorem thm_nat_refl_{j} (n : Nat) : n = n",
        lambda j: f"theorem thm_nat_add_{j} (n m : Nat) : n + m = m + n",
        lambda j: f"theorem thm_bool_refl_{j} (b : Bool) : b = b",
        lambda j: f"theorem thm_prop_id_{j} (P : Prop) : P -> P",
        lambda j: f"theorem thm_prop_left_{j} (P Q : Prop) : P -> Q -> P",
        lambda j: f"theorem thm_list_len_{j} (xs : List Nat) : xs.length = xs.length",
    )
    return rng.choice(builders)(i)


def _corrupt_unknown_type_symbol(target: str, rng: random.Random) -> str:
    candidates = [source for source in ("List Nat", "Nat", "Bool", "Prop") if source in target]
    if candidates:
        return target.replace(rng.choice(candidates), "Foo", 1)
    return target


def _corrupt_lowercase_type(target: str, rng: random.Random) -> str:
    replacements = (
        ("List Nat", "list nat"),
        ("Nat", "nat"),
        ("Bool", "bool"),
        ("Prop", "prop"),
    )
    candidates = [(source, replacement) for source, replacement in replacements if source in target]
    if candidates:
        source, replacement = rng.choice(candidates)
        return target.replace(source, replacement, 1)
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
    names = _binder_names(target[:colon])
    fallback = rng.choice(names) if names else "Nat"
    return f"{target[: colon + 1]} {fallback}"


def _corrupt_type_mismatch(target: str, rng: random.Random) -> str:
    colon = _find_top_level_colon(target)
    if colon == -1:
        return target
    goal = target[colon + 1 :].strip()
    if "=" in goal:
        left, _ = goal.split("=", 1)
        rhs = rng.choice(["True", "False"])
        return f"{target[: colon + 1]} {left.strip()} = {rhs}"
    if "->" in goal:
        left, _ = goal.rsplit("->", 1)
        rhs = rng.choice(["Nat", "Bool"])
        return f"{target[: colon + 1]} {left.strip()} -> {rhs}"
    return f"{target[: colon + 1]} Nat = True"


def _binder_names(prefix: str) -> list[str]:
    names: list[str] = []
    for group in re.findall(r"\(([^)]*)\)", prefix):
        if ":" not in group:
            continue
        raw_names = group.split(":", 1)[0]
        for name in raw_names.split():
            cleaned = name.strip()
            if cleaned and re.fullmatch(r"[A-Za-z_][\w']*", cleaned):
                names.append(cleaned)
    return names


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


if __name__ == "__main__":
    raise SystemExit(main())
