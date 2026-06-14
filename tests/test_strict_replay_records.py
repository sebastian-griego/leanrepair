import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from jsonl_io import JsonlError  # noqa: E402
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
