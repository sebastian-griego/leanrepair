import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from jsonl_io import JsonlError  # noqa: E402
import strict_replay_analysis as sra  # noqa: E402
import strict_replay_records as srr  # noqa: E402


def test_load_records_jsonl_accepts_full_replay_schema(tmp_path):
    path = tmp_path / "strict_replay_records.jsonl"
    path.write_text(json.dumps(_row("run_001", "a", "research")) + "\n", encoding="utf-8")

    rows = srr.load_records_jsonl(path)

    assert rows[0]["run"] == "run_001"
    assert rows[0]["id"] == "a"
    assert rows[0]["policy"] == "research"


def test_load_records_jsonl_rejects_duplicate_composite_keys(tmp_path):
    path = tmp_path / "strict_replay_records.jsonl"
    path.write_text(
        json.dumps(_row("run_001", "a", "research"))
        + "\n\n"
        + json.dumps(_row("run_001", "a", "research"))
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(JsonlError) as excinfo:
        srr.load_records_jsonl(path)

    message = str(excinfo.value)
    assert f"{path}:3" in message
    assert "duplicate strict replay row run='run_001', id='a', policy='research'" in message
    assert "first seen at line 1" in message


def test_load_records_jsonl_rejects_missing_required_field(tmp_path):
    path = tmp_path / "strict_replay_records.jsonl"
    row = _row("run_001", "a", "research")
    del row["reported_ok"]
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(JsonlError) as excinfo:
        srr.load_records_jsonl(path)

    assert f"{path}:1" in str(excinfo.value)
    assert "missing reported_ok" in str(excinfo.value)


def test_load_records_jsonl_rejects_inconsistent_exact_flag(tmp_path):
    path = tmp_path / "strict_replay_records.jsonl"
    row = _row("run_001", "a", "research", strict_ok=False, strict_exact=True)
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(JsonlError) as excinfo:
        srr.load_records_jsonl(path)

    assert f"{path}:1" in str(excinfo.value)
    assert "strict_exact is true but strict_ok is false" in str(excinfo.value)


def test_validate_records_rejects_step_flag_mismatches():
    raw_ok_missing_step = _row("run_001", "a", "research")
    raw_ok_missing_step["raw_step_index"] = None
    with pytest.raises(JsonlError, match="raw_ok is true but raw_step_index is null"):
        srr.validate_records([raw_ok_missing_step])

    raw_fail_with_step = _row(
        "run_001", "b", "research", raw_ok=False, strict_ok=False, strict_exact=False
    )
    raw_fail_with_step["raw_step_index"] = 1
    with pytest.raises(JsonlError, match="raw_step_index is set but raw_ok is false"):
        srr.validate_records([raw_fail_with_step])

    strict_ok_missing_step = _row("run_001", "c", "research")
    strict_ok_missing_step["strict_step_index"] = None
    with pytest.raises(JsonlError, match="strict_ok is true but strict_step_index is null"):
        srr.validate_records([strict_ok_missing_step])

    strict_fail_with_step = _row(
        "run_001", "d", "research", strict_ok=False, strict_exact=False
    )
    strict_fail_with_step["strict_step_index"] = 1
    with pytest.raises(JsonlError, match="strict_step_index is set but strict_ok is false"):
        srr.validate_records([strict_fail_with_step])


def test_validate_records_rejects_replay_state_inconsistencies():
    raw_degenerate_without_reason = _row("run_001", "a", "research")
    raw_degenerate_without_reason["raw_degenerate"] = True
    raw_degenerate_without_reason["raw_reason"] = ""
    with pytest.raises(JsonlError, match="raw_degenerate is true but raw_reason is empty"):
        srr.validate_records([raw_degenerate_without_reason])

    recovered_without_discarded = _row("run_001", "b", "research")
    recovered_without_discarded["raw_degenerate"] = True
    recovered_without_discarded["raw_reason"] = "goal_true"
    recovered_without_discarded["recovered_after_degenerate"] = True
    recovered_without_discarded["discarded_degenerate_ok_steps"] = 0
    with pytest.raises(JsonlError, match="no degenerate steps were discarded"):
        srr.validate_records([recovered_without_discarded])

    changed_flag_mismatch = _row("run_001", "c", "research")
    changed_flag_mismatch["strict_final_header"] = "theorem c : Nat := by exact 0"
    changed_flag_mismatch["changed_accepted_output"] = False
    with pytest.raises(JsonlError, match="changed_accepted_output does not match"):
        srr.validate_records([changed_flag_mismatch])


def test_write_replay_records_jsonl_validates_export_rows(tmp_path):
    path = tmp_path / "strict_replay_records.jsonl"
    rows = [
        _row("run_001", "a", "research"),
        _row("run_001", "a", "research"),
    ]

    with pytest.raises(JsonlError, match="duplicate strict replay row"):
        sra.write_replay_records_jsonl(path, rows)

    assert not path.exists()


def _row(
    run: str,
    item_id: str,
    policy: str,
    *,
    raw_ok: bool = True,
    strict_ok: bool = True,
    strict_exact: bool = True,
) -> dict:
    return {
        "run": run,
        "id": item_id,
        "policy": policy,
        "corruption": "parse",
        "reported_ok": raw_ok,
        "raw_ok": raw_ok,
        "raw_exact": strict_exact,
        "raw_degenerate": False,
        "raw_reason": "",
        "raw_step_index": 1 if raw_ok else None,
        "raw_final_header": f"theorem {item_id} : True" if raw_ok else "",
        "raw_final_goal": "True" if raw_ok else "",
        "target_header": f"theorem {item_id} : True",
        "target_goal": "True",
        "strict_ok": strict_ok,
        "strict_exact": strict_exact,
        "strict_step_index": 1 if strict_ok else None,
        "strict_final_header": f"theorem {item_id} : True" if strict_ok else "",
        "strict_final_goal": "True" if strict_ok else "",
        "discarded_degenerate_ok_steps": 0,
        "recovered_after_degenerate": False,
        "changed_accepted_output": False,
    }
