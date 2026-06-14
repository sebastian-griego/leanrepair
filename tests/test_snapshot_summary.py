import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts.summarize_real_paper_snapshot import build_snapshot, format_markdown  # noqa: E402


def test_real_paper_snapshot_rollup_merges_result_artifacts(tmp_path):
    root = tmp_path / "real_paper_v2"
    root.mkdir()
    _write(root / "aggregate_summary.json", _aggregate())
    _write(root / "quality_summary.json", _quality())
    _write(root / "semantic_drift.json", _semantic())
    _write(root / "strict_replay.json", _strict())
    _write(root / "strict_replay_casebook.json", _casebook())
    _write(root / "strict_replay_paired.json", _paired())

    snapshot = build_snapshot(root)
    markdown = format_markdown(snapshot)

    assert snapshot["dataset"]["n_runs"] == 2
    assert snapshot["aggregate"]["research"]["solved"] == 16
    assert snapshot["quality_adjusted"]["research"]["nondegenerate_solved"] == 6
    assert snapshot["semantic_drift"]["research"]["degenerate_reasons"] == {"goal_true": 10}
    assert snapshot["strict_replay"]["research"]["strict_exact"] == 5
    assert snapshot["strict_casebook"]["flag_counts"]["raw_to_strict_loss"] == 13
    assert snapshot["strict_paired"]["metrics"]["strict_ok"]["policy_b_only"] == 6
    assert snapshot["strict_paired"]["raw_win_loss"]["by_reason"][0]["name"] == "goal_true"
    assert "LeanRepair Real Paper v2 Snapshot" in markdown
    assert "Strict Paired Comparison" in markdown


def _write(path: pathlib.Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _aggregate() -> dict:
    return {
        "runs": ["run_a", "run_b"],
        "n_runs": 2,
        "policies": {
            "heuristic": _aggregate_policy(20, 2, 0, 0.1, 0.0),
            "research": _aggregate_policy(20, 16, 5, 0.8, 0.25),
        },
    }


def _aggregate_policy(count, solved, exact, solve_rate, exact_rate) -> dict:
    return {
        "solve_rate_mean": solve_rate,
        "solve_rate_std": 0.01,
        "exact_rate_mean": exact_rate,
        "exact_rate_std": 0.02,
        "pooled": {
            "count": count,
            "solved": solved,
            "exact": exact,
            "solve_rate": solve_rate,
            "solve_rate_ci95": [solve_rate, solve_rate],
            "exact_rate": exact_rate,
            "exact_rate_ci95": [exact_rate, exact_rate],
        },
    }


def _quality() -> dict:
    return {
        "policies": {
            "heuristic": _quality_policy(20, 2, 0, 0, 2, 0.0, 1.0),
            "research": _quality_policy(20, 16, 5, 6, 10, 0.3, 0.625),
        }
    }


def _quality_policy(count, solved, exact, nondegenerate, degenerate, nondeg_rate, deg_given) -> dict:
    return {
        "pooled": {
            "count": count,
            "solved": solved,
            "exact": exact,
            "nondegenerate_solved": nondegenerate,
            "degenerate_solved": degenerate,
            "nondegenerate_solved_rate": nondeg_rate,
            "nondegenerate_solved_rate_ci95": [nondeg_rate, nondeg_rate],
            "degenerate_given_solved": deg_given,
        }
    }


def _semantic() -> dict:
    return {
        "policies": {
            "heuristic": _semantic_policy(20, 2, 0, 2, 0, {"reflexive_equality": 2}),
            "research": _semantic_policy(20, 16, 5, 10, 6, {"goal_true": 10}),
        }
    }


def _semantic_policy(count, solved, exact, degenerate, nondegenerate, reasons) -> dict:
    return {
        "count": count,
        "solved": solved,
        "exact": exact,
        "degenerate_solved": degenerate,
        "nondegenerate_solved": nondegenerate,
        "degenerate_reasons": reasons,
        "degenerate_given_solved": degenerate / solved if solved else 0.0,
    }


def _strict() -> dict:
    return {
        "policies": {
            "heuristic": _strict_policy(20, 2, 0, 0, 0, 2, {"reflexive_equality": 2}),
            "research": _strict_policy(20, 16, 6, 5, 1, 10, {"goal_true": 10}),
        }
    }


def _strict_policy(count, raw_solved, strict_solved, exact, nonexact, loss, reasons) -> dict:
    return {
        "count": count,
        "raw_solved": raw_solved,
        "strict_solved": strict_solved,
        "raw_exact": exact,
        "strict_exact": exact,
        "strict_not_exact": nonexact,
        "raw_degenerate_solved": loss,
        "raw_to_strict_loss": loss,
        "strict_retention_given_raw": strict_solved / raw_solved if raw_solved else 0.0,
        "strict_exact_given_strict": exact / strict_solved if strict_solved else 0.0,
        "raw_degenerate_reasons": reasons,
    }


def _casebook() -> dict:
    return {
        "dataset": {"records": 40, "focused_cases": 14},
        "primary_case_counts": {"raw_to_strict_loss": 13, "strict_nonexact_accept": 1},
        "flag_counts": {"raw_to_strict_loss": 13, "strict_nonexact_accept": 1},
        "by_policy": {
            "heuristic": {"raw_to_strict_loss": 2},
            "research": {"raw_to_strict_loss": 11, "strict_nonexact_accept": 1},
        },
        "raw_loss_reasons": {"goal_true": 10, "reflexive_equality": 3},
    }


def _paired() -> dict:
    return {
        "policy_a": "heuristic",
        "policy_b": "research",
        "coverage": {
            "policy_a_records": 20,
            "policy_b_records": 20,
            "paired_records": 20,
            "policy_a_unpaired": 0,
            "policy_b_unpaired": 0,
        },
        "metrics": {
            "raw_ok": _paired_metric(2, 16, 14, 0, 0.7, 0.001),
            "strict_ok": _paired_metric(0, 6, 6, 0, 0.3, 0.01),
            "strict_exact": _paired_metric(0, 5, 5, 0, 0.25, 0.02),
        },
        "case_counts": {"policy_b_raw_wins_lost_by_strict": 8},
        "raw_win_loss": {
            "total": 8,
            "by_reason": [{"name": "goal_true", "count": 8, "share": 1.0}],
        },
    }


def _paired_metric(a_success, b_success, b_only, a_only, lift, pvalue) -> dict:
    return {
        "policy_a_successes": a_success,
        "policy_b_successes": b_success,
        "policy_a_only": a_only,
        "policy_b_only": b_only,
        "policy_b_lift": lift,
        "paired_exact_sign_p_two_sided": pvalue,
    }
