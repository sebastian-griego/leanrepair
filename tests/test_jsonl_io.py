import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from jsonl_io import (  # noqa: E402
    JsonlError,
    iter_jsonl_objects,
    load_jsonl_map_by_key,
    load_jsonl_objects,
    load_jsonl_objects_unique_by_key,
    load_policy_result_map,
    load_policy_result_objects,
)


def test_load_jsonl_objects_skips_blank_lines(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "a"}\n\n{"id": "b"}\n', encoding="utf-8")

    assert load_jsonl_objects(path) == [{"id": "a"}, {"id": "b"}]


def test_iter_jsonl_objects_reports_physical_line_numbers(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "a"}\n\n{"id": "b"}\n', encoding="utf-8")

    assert list(iter_jsonl_objects(path)) == [
        (1, {"id": "a"}),
        (3, {"id": "b"}),
    ]


def test_load_jsonl_objects_reports_invalid_json_line(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "a"}\n\n{"id": bad}\n', encoding="utf-8")

    with pytest.raises(JsonlError) as excinfo:
        load_jsonl_objects(path)

    assert f"{path}:3" in str(excinfo.value)
    assert "Invalid JSON" in str(excinfo.value)


def test_load_jsonl_objects_requires_object_rows(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "a"}\n[1, 2, 3]\n', encoding="utf-8")

    with pytest.raises(JsonlError) as excinfo:
        load_jsonl_objects(path)

    assert f"{path}:2" in str(excinfo.value)
    assert "Expected JSON object" in str(excinfo.value)


def test_load_jsonl_map_by_key_rejects_missing_key(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "a"}\n{"missing": true}\n', encoding="utf-8")

    with pytest.raises(JsonlError) as excinfo:
        load_jsonl_map_by_key(path, "id")

    assert f"{path}:2" in str(excinfo.value)
    assert "missing id" in str(excinfo.value)


def test_load_jsonl_map_by_key_rejects_duplicate_key(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "a"}\n\n{"id": "a"}\n', encoding="utf-8")

    with pytest.raises(JsonlError) as excinfo:
        load_jsonl_map_by_key(path, "id")

    message = str(excinfo.value)
    assert f"{path}:3" in message
    assert "duplicate id 'a'" in message
    assert "first seen at line 1" in message


def test_load_jsonl_objects_unique_by_key_preserves_order(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "a"}\n{"id": "b"}\n', encoding="utf-8")

    assert load_jsonl_objects_unique_by_key(path, "id") == [{"id": "a"}, {"id": "b"}]


def test_load_jsonl_objects_unique_by_key_rejects_duplicates(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text(
        '{"id": "a", "value": 1}\n\n{"id": "a", "value": 2}\n',
        encoding="utf-8",
    )

    with pytest.raises(JsonlError) as excinfo:
        load_jsonl_objects_unique_by_key(path, "id")

    message = str(excinfo.value)
    assert f"{path}:3" in message
    assert "duplicate id 'a'" in message
    assert "first seen at line 1" in message


def test_load_policy_result_objects_rejects_exact_without_ok(tmp_path):
    path = tmp_path / "policy.jsonl"
    path.write_text('{"id": "a", "ok": false, "exact": true}\n', encoding="utf-8")

    with pytest.raises(JsonlError) as excinfo:
        load_policy_result_objects(path)

    message = str(excinfo.value)
    assert f"{path}:1" in message
    assert "exact is true but ok is false" in message


def test_load_policy_result_map_rejects_non_bool_outcome_fields(tmp_path):
    path = tmp_path / "policy.jsonl"
    path.write_text('{"id": "a", "ok": "true", "exact": false}\n', encoding="utf-8")

    with pytest.raises(JsonlError) as excinfo:
        load_policy_result_map(path)

    message = str(excinfo.value)
    assert f"{path}:1" in message
    assert "expected ok to be bool" in message
