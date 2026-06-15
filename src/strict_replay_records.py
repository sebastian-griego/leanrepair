from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from jsonl_io import JsonlError, iter_jsonl_objects


KEY_FIELDS = ("run", "id", "policy")
REQUIRED_FIELDS = (
    "run",
    "id",
    "policy",
    "corruption",
    "reported_ok",
    "raw_ok",
    "raw_exact",
    "raw_degenerate",
    "raw_reason",
    "raw_step_index",
    "raw_final_header",
    "raw_final_goal",
    "target_header",
    "target_goal",
    "strict_ok",
    "strict_exact",
    "strict_step_index",
    "strict_final_header",
    "strict_final_goal",
    "discarded_degenerate_ok_steps",
    "recovered_after_degenerate",
    "changed_accepted_output",
)
BOOL_FIELDS = (
    "reported_ok",
    "raw_ok",
    "raw_exact",
    "raw_degenerate",
    "strict_ok",
    "strict_exact",
    "recovered_after_degenerate",
    "changed_accepted_output",
)
TEXT_FIELDS = (
    "run",
    "id",
    "policy",
    "corruption",
    "raw_reason",
    "raw_final_header",
    "raw_final_goal",
    "target_header",
    "target_goal",
    "strict_final_header",
    "strict_final_goal",
)
STEP_FIELDS = ("raw_step_index", "strict_step_index")


def load_records_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    first_lines: dict[tuple[str, str, str], int] = {}
    path = Path(path)
    for line_no, row in iter_jsonl_objects(path):
        validate_record(row, path=path, line_no=line_no)
        key = _record_key(row)
        if key in first_lines:
            run, item_id, policy = key
            raise JsonlError(
                "duplicate strict replay row "
                f"run={run!r}, id={item_id!r}, policy={policy!r} "
                f"at {path}:{line_no}; first seen at line {first_lines[key]}"
            )
        first_lines[key] = line_no
        rows.append(row)
    return rows


def validate_records(
    records: Iterable[object],
    *,
    location: str = "input strict replay records",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    first_rows: dict[tuple[str, str, str], int] = {}
    for row_no, row in enumerate(records, start=1):
        if not isinstance(row, dict):
            raise JsonlError(
                f"expected {location} row {row_no} to be dict, got {type(row).__name__}"
            )
        validate_record(row, path=location, line_no=row_no)
        key = _record_key(row)
        if key in first_rows:
            run, item_id, policy = key
            raise JsonlError(
                "duplicate strict replay row "
                f"run={run!r}, id={item_id!r}, policy={policy!r} "
                f"at input row {row_no}; first seen at input row {first_rows[key]}"
            )
        first_rows[key] = row_no
        rows.append(row)
    return rows


def validate_record(
    row: dict[str, Any],
    *,
    path: str | Path | None = None,
    line_no: int | None = None,
) -> None:
    location = _location(path, line_no)
    for field in REQUIRED_FIELDS:
        if field not in row:
            raise JsonlError(f"missing {field} at {location}")

    for field in TEXT_FIELDS:
        if not isinstance(row[field], str):
            raise JsonlError(
                f"expected {field} to be str at {location}, got {type(row[field]).__name__}"
            )

    for field in KEY_FIELDS:
        if not row[field].strip():
            raise JsonlError(f"empty {field} at {location}")

    for field in BOOL_FIELDS:
        if not isinstance(row[field], bool):
            raise JsonlError(
                f"expected {field} to be bool at {location}, got {type(row[field]).__name__}"
            )

    for field in STEP_FIELDS:
        value = row[field]
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise JsonlError(
                f"expected {field} to be int or null at {location}, got {type(value).__name__}"
            )
        if isinstance(value, int) and value < 1:
            raise JsonlError(f"expected {field} to be positive at {location}, got {value}")

    discarded = row["discarded_degenerate_ok_steps"]
    if not isinstance(discarded, int) or isinstance(discarded, bool):
        raise JsonlError(
            "expected discarded_degenerate_ok_steps to be int "
            f"at {location}, got {type(discarded).__name__}"
        )
    if discarded < 0:
        raise JsonlError(
            f"expected discarded_degenerate_ok_steps to be nonnegative at {location}, got {discarded}"
        )

    if row["raw_exact"] and not row["raw_ok"]:
        raise JsonlError(f"raw_exact is true but raw_ok is false at {location}")
    if row["strict_exact"] and not row["strict_ok"]:
        raise JsonlError(f"strict_exact is true but strict_ok is false at {location}")
    if row["strict_ok"] and not row["raw_ok"]:
        raise JsonlError(f"strict_ok is true but raw_ok is false at {location}")
    if row["raw_ok"] and row["raw_step_index"] is None:
        raise JsonlError(f"raw_ok is true but raw_step_index is null at {location}")
    if not row["raw_ok"] and row["raw_step_index"] is not None:
        raise JsonlError(f"raw_step_index is set but raw_ok is false at {location}")
    if row["strict_ok"] and row["strict_step_index"] is None:
        raise JsonlError(
            f"strict_ok is true but strict_step_index is null at {location}"
        )
    if not row["strict_ok"] and row["strict_step_index"] is not None:
        raise JsonlError(
            f"strict_step_index is set but strict_ok is false at {location}"
        )
    if row["raw_ok"] and not row["raw_final_header"].strip():
        raise JsonlError(f"raw_ok is true but raw_final_header is empty at {location}")
    if row["strict_ok"] and not row["strict_final_header"].strip():
        raise JsonlError(
            f"strict_ok is true but strict_final_header is empty at {location}"
        )
    if row["raw_degenerate"] and not row["raw_ok"]:
        raise JsonlError(f"raw_degenerate is true but raw_ok is false at {location}")
    if row["raw_degenerate"] and not row["raw_reason"].strip():
        raise JsonlError(f"raw_degenerate is true but raw_reason is empty at {location}")
    if row["raw_degenerate"] and discarded < 1:
        raise JsonlError(
            "raw_degenerate is true but no degenerate steps were discarded "
            f"at {location}"
        )
    if discarded > 0 and not row["raw_degenerate"]:
        raise JsonlError(
            "discarded_degenerate_ok_steps is positive but raw_degenerate is false "
            f"at {location}"
        )
    if (
        row["raw_degenerate"]
        and row["strict_ok"]
        and not row["recovered_after_degenerate"]
    ):
        raise JsonlError(
            "raw_degenerate and strict_ok require recovered_after_degenerate "
            f"at {location}"
        )
    if row["recovered_after_degenerate"] and not (
        row["raw_degenerate"] and row["strict_ok"]
    ):
        raise JsonlError(
            "recovered_after_degenerate requires raw_degenerate and strict_ok "
            f"at {location}"
        )
    if row["recovered_after_degenerate"] and discarded < 1:
        raise JsonlError(
            "recovered_after_degenerate is true but no degenerate steps were "
            f"discarded at {location}"
        )
    if row["recovered_after_degenerate"] and (
        row["strict_step_index"] <= row["raw_step_index"]
    ):
        raise JsonlError(
            "recovered_after_degenerate requires strict_step_index after raw_step_index "
            f"at {location}"
        )
    if row["changed_accepted_output"] and not row["strict_ok"]:
        raise JsonlError(f"changed_accepted_output is true but strict_ok is false at {location}")
    changed_output = row["raw_final_header"] != row["strict_final_header"]
    if row["raw_ok"] and row["strict_ok"] and row["changed_accepted_output"] != changed_output:
        expected = str(changed_output).lower()
        raise JsonlError(
            "changed_accepted_output does not match raw/strict final headers "
            f"at {location}; expected {expected}"
        )


def _record_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (str(row["run"]), str(row["id"]), str(row["policy"]))


def _location(path: str | Path | None, line_no: int | None) -> str:
    if path is None:
        return "strict replay record"
    if line_no is None:
        return str(Path(path))
    return f"{Path(path)}:{line_no}"


__all__ = [
    "BOOL_FIELDS",
    "KEY_FIELDS",
    "REQUIRED_FIELDS",
    "STEP_FIELDS",
    "TEXT_FIELDS",
    "load_records_jsonl",
    "validate_record",
    "validate_records",
]
