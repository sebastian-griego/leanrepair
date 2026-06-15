import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "src"))

import budget_analysis as ba  # noqa: E402
import exactness_analysis as ea  # noqa: E402
from jsonl_io import JsonlError  # noqa: E402
import semantic_drift_analysis as sda  # noqa: E402
import strict_replay_analysis as sra  # noqa: E402
import trace_analysis as ta  # noqa: E402
from scripts import analyze_paired_results as apr  # noqa: E402


POLICY_RESULT_LOADERS = (
    pytest.param(ba.load_jsonl, id="budget"),
    pytest.param(ea.load_jsonl, id="exactness"),
    pytest.param(sda.load_jsonl, id="semantic_drift"),
    pytest.param(sra.load_jsonl, id="strict_replay"),
    pytest.param(ta.load_jsonl, id="trace"),
    pytest.param(apr._load_policy_rows, id="paired"),
)


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


@pytest.mark.parametrize("loader", POLICY_RESULT_LOADERS)
def test_policy_result_loaders_reject_exact_without_ok(loader, tmp_path):
    path = tmp_path / "research.jsonl"
    _write_jsonl(path, [{"id": "bad", "ok": False, "exact": True}])

    with pytest.raises(JsonlError) as excinfo:
        loader(path)

    message = str(excinfo.value)
    assert f"{path}:1" in message
    assert "exact is true but ok is false" in message


@pytest.mark.parametrize("loader", POLICY_RESULT_LOADERS)
def test_policy_result_loaders_reject_non_boolean_ok_exact(loader, tmp_path):
    path = tmp_path / "research.jsonl"
    _write_jsonl(path, [{"id": "bad", "ok": "true", "exact": False}])

    with pytest.raises(JsonlError) as excinfo:
        loader(path)

    message = str(excinfo.value)
    assert f"{path}:1" in message
    assert "expected ok to be bool" in message


def _write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
