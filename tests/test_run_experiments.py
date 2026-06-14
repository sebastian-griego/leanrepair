import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "src"))

from jsonl_io import JsonlError  # noqa: E402
from scripts import run_experiments as rex  # noqa: E402


def test_load_benchmark_rejects_missing_required_field_with_line_number(tmp_path):
    path = tmp_path / "benchmark.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "bad",
                "nl": "",
                "ctx": "",
                "candidate": "theorem bad : True",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(JsonlError) as excinfo:
        rex._load_benchmark(path)

    assert f"{path}:1" in str(excinfo.value)
    assert "'target'" in str(excinfo.value)


def test_run_experiments_rejects_bad_schema_before_creating_run_dir(tmp_path):
    path = tmp_path / "benchmark.jsonl"
    output_dir = tmp_path / "results"
    path.write_text(
        json.dumps(
            {
                "id": "bad",
                "nl": "",
                "ctx": "",
                "candidate": ["not", "a", "string"],
                "target": "theorem bad : True",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(JsonlError) as excinfo:
        rex.main(["--input", str(path), "--output-dir", str(output_dir)])

    assert f"{path}:1" in str(excinfo.value)
    assert "'candidate'" in str(excinfo.value)
    assert not output_dir.exists()


def test_load_benchmark_rejects_empty_file(tmp_path):
    path = tmp_path / "benchmark.jsonl"
    path.write_text("\n\n", encoding="utf-8")

    with pytest.raises(JsonlError) as excinfo:
        rex._load_benchmark(path)

    assert f"Empty benchmark at {path}" in str(excinfo.value)
