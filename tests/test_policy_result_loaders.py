import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

import budget_analysis as ba  # noqa: E402
import exactness_analysis as ea  # noqa: E402
from jsonl_io import JsonlError  # noqa: E402
import semantic_drift_analysis as sda  # noqa: E402
import strict_replay_analysis as sra  # noqa: E402
import trace_analysis as ta  # noqa: E402


@pytest.mark.parametrize(
    "module",
    [ba, ea, sda, sra, ta],
    ids=[
        "budget",
        "exactness",
        "semantic_drift",
        "strict_replay",
        "trace",
    ],
)
def test_policy_result_loaders_reject_duplicate_ids(module, tmp_path):
    path = tmp_path / "research.jsonl"
    _write_jsonl(
        path,
        [
            {"id": "dup", "ok": False, "exact": False},
            {"id": "dup", "ok": True, "exact": True},
        ],
    )

    with pytest.raises(JsonlError) as excinfo:
        module.load_jsonl(path)

    message = str(excinfo.value)
    assert f"{path}:2" in message
    assert "duplicate id 'dup'" in message
    assert "first seen at line 1" in message


@pytest.mark.parametrize(
    "module",
    [ba, ea, sda, sra, ta],
    ids=[
        "budget",
        "exactness",
        "semantic_drift",
        "strict_replay",
        "trace",
    ],
)
def test_policy_result_loaders_reject_missing_ids(module, tmp_path):
    path = tmp_path / "research.jsonl"
    _write_jsonl(path, [{"ok": False, "exact": False}])

    with pytest.raises(JsonlError) as excinfo:
        module.load_jsonl(path)

    message = str(excinfo.value)
    assert f"{path}:1" in message
    assert "missing id" in message


def _write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
