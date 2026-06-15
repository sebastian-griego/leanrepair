from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


class JsonlError(ValueError):
    """Raised when a JSONL artifact has an invalid row."""


def iter_jsonl_objects(path: str | Path) -> Iterator[tuple[int, dict[str, Any]]]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise JsonlError(f"Invalid JSON at {path}:{line_no}: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise JsonlError(
                    f"Expected JSON object at {path}:{line_no}, got {type(row).__name__}"
                )
            yield line_no, row


def load_jsonl_objects(path: str | Path) -> list[dict[str, Any]]:
    return [row for _line_no, row in iter_jsonl_objects(path)]


def load_jsonl_objects_unique_by_key(path: str | Path, key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    first_lines: dict[str, int] = {}
    path = Path(path)
    for line_no, row in iter_jsonl_objects(path):
        value = row.get(key)
        if value is None:
            raise JsonlError(f"missing {key} at {path}:{line_no}")
        map_key = str(value)
        if map_key in first_lines:
            raise JsonlError(
                f"duplicate {key} {map_key!r} at {path}:{line_no}; "
                f"first seen at line {first_lines[map_key]}"
            )
        first_lines[map_key] = line_no
        rows.append(row)
    return rows


def load_jsonl_map_by_key(path: str | Path, key: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    first_lines: dict[str, int] = {}
    path = Path(path)
    for line_no, row in iter_jsonl_objects(path):
        value = row.get(key)
        if value is None:
            raise JsonlError(f"missing {key} at {path}:{line_no}")
        map_key = str(value)
        if map_key in rows:
            raise JsonlError(
                f"duplicate {key} {map_key!r} at {path}:{line_no}; "
                f"first seen at line {first_lines[map_key]}"
            )
        rows[map_key] = row
        first_lines[map_key] = line_no
    return rows


def load_policy_result_objects(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    first_lines: dict[str, int] = {}
    path = Path(path)
    for line_no, row in iter_jsonl_objects(path):
        _validate_policy_result_row(row, path=path, line_no=line_no)
        map_key = _require_unique_key(
            row,
            "id",
            path=path,
            line_no=line_no,
            first_lines=first_lines,
        )
        first_lines[map_key] = line_no
        rows.append(row)
    return rows


def load_policy_result_map(path: str | Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    first_lines: dict[str, int] = {}
    path = Path(path)
    for line_no, row in iter_jsonl_objects(path):
        _validate_policy_result_row(row, path=path, line_no=line_no)
        map_key = _require_unique_key(
            row,
            "id",
            path=path,
            line_no=line_no,
            first_lines=first_lines,
        )
        rows[map_key] = row
        first_lines[map_key] = line_no
    return rows


def _validate_policy_result_row(row: dict[str, Any], *, path: Path, line_no: int) -> None:
    for field in ("ok", "exact"):
        if field in row and not isinstance(row[field], bool):
            raise JsonlError(
                f"expected {field} to be bool at {path}:{line_no}, "
                f"got {type(row[field]).__name__}"
            )
    if row.get("exact") is True and row.get("ok") is not True:
        raise JsonlError(f"exact is true but ok is false at {path}:{line_no}")


def _require_unique_key(
    row: dict[str, Any],
    key: str,
    *,
    path: Path,
    line_no: int,
    first_lines: dict[str, int],
) -> str:
    value = row.get(key)
    if value is None:
        raise JsonlError(f"missing {key} at {path}:{line_no}")
    map_key = str(value)
    if map_key in first_lines:
        raise JsonlError(
            f"duplicate {key} {map_key!r} at {path}:{line_no}; "
            f"first seen at line {first_lines[map_key]}"
        )
    return map_key


__all__ = [
    "JsonlError",
    "iter_jsonl_objects",
    "load_jsonl_map_by_key",
    "load_jsonl_objects",
    "load_jsonl_objects_unique_by_key",
    "load_policy_result_map",
    "load_policy_result_objects",
]
