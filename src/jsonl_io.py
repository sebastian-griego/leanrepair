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


__all__ = ["JsonlError", "iter_jsonl_objects", "load_jsonl_objects"]
