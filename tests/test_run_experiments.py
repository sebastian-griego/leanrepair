import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "src"))

from jsonl_io import JsonlError  # noqa: E402
from artifact_manifest import verify_manifest  # noqa: E402
import lean_check as lc  # noqa: E402
from scripts import run_experiments as rex  # noqa: E402


def _write_smoke_benchmark(path: pathlib.Path) -> None:
    path.write_text(
        json.dumps(
            {
                "id": "item_1",
                "nl": "",
                "ctx": "",
                "candidate": "theorem item_1 : True",
                "target": "theorem item_1 : True",
                "corruption": "smoke",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _patch_successful_lean(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_lean_check(ctx: str, theorem: str, timeout_s: float) -> lc.CheckResult:
        return lc.CheckResult(
            ok=True,
            errors=[],
            raw="",
            elapsed_ms=1,
            timed_out=False,
        )

    monkeypatch.setattr(rex.rl.lc, "lean_check", fake_lean_check)


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


def test_run_experiments_writes_verifiable_manifest(tmp_path, monkeypatch):
    input_path = tmp_path / "benchmark.jsonl"
    output_dir = tmp_path / "results"
    _write_smoke_benchmark(input_path)
    _patch_successful_lean(monkeypatch)

    exit_code = rex.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--policies",
            "heuristic",
            "--Tmax",
            "1",
            "--timeout-s",
            "1",
        ]
    )

    assert exit_code == 0
    run_dir = next(output_dir.glob("run_*"))
    manifest = verify_manifest(run_dir)
    paths = {entry["path"] for entry in manifest["artifacts"]}
    assert "heuristic.jsonl" in paths
    assert "summary.json" in paths
    assert "report.md" in paths
    for entry in manifest["artifacts"]:
        artifact_bytes = (run_dir / entry["path"]).read_bytes()
        assert b"\r\n" not in artifact_bytes, entry["path"]
    manifest_bytes = (run_dir / "manifest.json").read_bytes()
    assert manifest_bytes.endswith(b"\n")
    assert b"\r\n" not in manifest_bytes


def test_run_experiments_suffixes_colliding_run_timestamp(tmp_path, monkeypatch):
    input_path = tmp_path / "benchmark.jsonl"
    output_dir = tmp_path / "results"
    _write_smoke_benchmark(input_path)
    _patch_successful_lean(monkeypatch)
    monkeypatch.setattr(rex, "_utc_run_timestamp", lambda: "20260615_120000")

    args = [
        "--input",
        str(input_path),
        "--output-dir",
        str(output_dir),
        "--policies",
        "heuristic",
        "--Tmax",
        "1",
        "--timeout-s",
        "1",
    ]

    assert rex.main(args) == 0
    assert rex.main(args) == 0

    run_dirs = sorted(path for path in output_dir.iterdir() if path.is_dir())
    assert [path.name for path in run_dirs] == [
        "run_20260615_120000",
        "run_20260615_120000_001",
    ]
    for run_dir in run_dirs:
        manifest = verify_manifest(run_dir)
        assert manifest["artifact_count"] > 0
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        assert summary["run_id"] == run_dir.name
