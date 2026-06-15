import json
import pathlib
import subprocess
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from artifact_manifest import ManifestError, verify_manifest, write_manifest  # noqa: E402


def test_write_and_verify_manifest_records_nested_artifacts(tmp_path):
    run_dir = tmp_path / "run_001"
    (run_dir / "nested").mkdir(parents=True)
    (run_dir / "summary.json").write_text('{"ok": true}\n', encoding="utf-8")
    (run_dir / "nested" / "trace.jsonl").write_text(
        '{"id": "a"}\n',
        encoding="utf-8",
    )
    (run_dir / "nested" / "manifest.json").write_text(
        '{"kind": "nested artifact"}\n',
        encoding="utf-8",
    )

    manifest = write_manifest(run_dir)

    paths = {entry["path"] for entry in manifest["artifacts"]}
    assert paths == {
        "nested/manifest.json",
        "nested/trace.jsonl",
        "summary.json",
    }
    assert (run_dir / "manifest.json").exists()
    verified = verify_manifest(run_dir)
    assert verified["artifact_count"] == 3


def test_verify_manifest_detects_tampered_artifact(tmp_path):
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()
    artifact = run_dir / "summary.json"
    artifact.write_text("abcd\n", encoding="utf-8")
    write_manifest(run_dir)

    artifact.write_text("abce\n", encoding="utf-8")

    with pytest.raises(ManifestError, match="sha256 mismatch"):
        verify_manifest(run_dir)


def test_verify_manifest_rejects_unlisted_extra_artifact(tmp_path):
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()
    (run_dir / "summary.json").write_text("{}\n", encoding="utf-8")
    write_manifest(run_dir)

    (run_dir / "late.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ManifestError, match="unexpected artifacts"):
        verify_manifest(run_dir)
    assert verify_manifest(run_dir, allow_extra=True)["artifact_count"] == 1


def test_verify_manifest_rejects_unlisted_nested_manifest(tmp_path):
    run_dir = tmp_path / "run_001"
    (run_dir / "nested").mkdir(parents=True)
    (run_dir / "summary.json").write_text("{}\n", encoding="utf-8")
    write_manifest(run_dir)

    (run_dir / "nested" / "manifest.json").write_text(
        '{"kind": "late"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="nested/manifest\\.json"):
        verify_manifest(run_dir)


def test_verify_manifest_rejects_path_escape(tmp_path):
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_count": 1,
                "artifacts": [
                    {
                        "path": "../outside.json",
                        "bytes": 2,
                        "sha256": "0" * 64,
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="manifest root"):
        verify_manifest(run_dir)


def test_verify_artifact_manifest_cli(tmp_path):
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()
    (run_dir / "summary.json").write_text("{}\n", encoding="utf-8")
    write_manifest(run_dir)

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "verify_artifact_manifest.py"),
            "--run-dir",
            str(run_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["verified"][0]["artifact_count"] == 1


def test_verify_artifact_manifest_cli_verifies_run_root(tmp_path):
    root = tmp_path / "runs"
    first = root / "run_001"
    second = root / "run_002"
    skipped = root / "scratch"
    first.mkdir(parents=True)
    second.mkdir()
    skipped.mkdir()
    (first / "summary.json").write_text("{}\n", encoding="utf-8")
    (second / "summary.json").write_text("{}\n", encoding="utf-8")
    (skipped / "summary.json").write_text("{}\n", encoding="utf-8")
    write_manifest(first)
    write_manifest(second)

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "verify_artifact_manifest.py"),
            "--root",
            str(root),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert [pathlib.Path(row["run_dir"]).name for row in payload["verified"]] == [
        "run_001",
        "run_002",
    ]
    assert [row["artifact_count"] for row in payload["verified"]] == [1, 1]
