import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from jsonl_io import JsonlError, load_jsonl_objects  # noqa: E402


def test_load_jsonl_objects_skips_blank_lines(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "a"}\n\n{"id": "b"}\n', encoding="utf-8")

    assert load_jsonl_objects(path) == [{"id": "a"}, {"id": "b"}]


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
