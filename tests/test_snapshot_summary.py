import json
import pathlib
import subprocess
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts.summarize_real_paper_snapshot import (  # noqa: E402
    _source_hash_mismatches,
    _stale_outputs,
    build_snapshot,
    format_markdown,
)


def test_real_paper_snapshot_rollup_merges_result_artifacts(tmp_path):
    root = tmp_path / "real_paper_v2"
    _write_snapshot_inputs(root)

    snapshot = build_snapshot(root)
    markdown = format_markdown(snapshot)

    assert snapshot["dataset"]["n_runs"] == 2
    assert set(snapshot["provenance"]["source_sha256"]) == set(snapshot["provenance"]["sources"])
    assert all(
        len(digest) == 64
        for digest in snapshot["provenance"]["source_sha256"].values()
    )
    assert _source_hash_mismatches(snapshot, base_dir=ROOT) == []
    assert snapshot["aggregate"]["research"]["solved"] == 16
    assert snapshot["budget_curve"]["research"]["final_budget"]["budget"] == 3
    assert snapshot["exactness_gap"]["research"]["solved_not_exact"] == 10
    assert snapshot["quality_adjusted"]["research"]["nondegenerate_solved"] == 6
    assert snapshot["semantic_drift"]["research"]["degenerate_reasons"] == {"goal_true": 10}
    assert snapshot["strict_replay"]["research"]["strict_exact"] == 5
    assert snapshot["strict_casebook"]["flag_counts"]["raw_to_strict_loss"] == 13
    assert snapshot["strict_paired"]["metrics"]["strict_ok"]["policy_b_only"] == 6
    assert snapshot["strict_paired"]["raw_win_loss"]["by_reason"][0]["name"] == "goal_true"
    assert snapshot["trace_taxonomy"]["research"]["top_terminal_failure"] == {
        "kind": "parse_error",
        "count": 4,
    }
    assert "LeanRepair Real Paper v2 Snapshot" in markdown
    assert "Repair Budget Curve" in markdown
    assert "Exactness Gap" in markdown
    assert "Trace Taxonomy" in markdown
    assert "Corruption Highlights" in markdown
    assert "Strict Paired Comparison" in markdown
    assert "sha256:" in markdown


def test_snapshot_rollup_rejects_inconsistent_policy_counts(tmp_path):
    root = tmp_path / "real_paper_v2"
    _write_snapshot_inputs(root)
    budget = _budget()
    budget["policies"]["research"]["count"] = 21
    _write(root / "budget_curve.json", budget)

    with pytest.raises(ValueError, match="budget_curve.research"):
        build_snapshot(root)


def test_snapshot_rollup_rejects_inconsistent_rates(tmp_path):
    root = tmp_path / "real_paper_v2"
    _write_snapshot_inputs(root)
    aggregate = _aggregate()
    aggregate["policies"]["research"]["pooled"]["solve_rate"] = 0.5
    _write(root / "aggregate_summary.json", aggregate)

    with pytest.raises(ValueError, match="aggregate.research.solve_rate"):
        build_snapshot(root)


def test_snapshot_check_cli_fails_without_rewriting_stale_outputs(tmp_path):
    root = tmp_path / "real_paper_v2"
    _write_snapshot_inputs(root)
    output_json = tmp_path / "snapshot.json"
    output_md = tmp_path / "snapshot.md"
    output_json.write_text("stale\n", encoding="utf-8")
    output_md.write_text("stale\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "summarize_real_paper_snapshot.py"),
            "--root",
            str(root),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--check",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "Stale snapshot outputs" in completed.stderr + completed.stdout
    assert output_json.read_text(encoding="utf-8") == "stale\n"
    assert output_md.read_text(encoding="utf-8") == "stale\n"


def test_snapshot_verify_source_hashes_cli_detects_changed_source(tmp_path):
    root = tmp_path / "real_paper_v2"
    _write_snapshot_inputs(root)
    output_json = tmp_path / "snapshot.json"
    output_md = tmp_path / "snapshot.md"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "summarize_real_paper_snapshot.py"),
            "--root",
            str(root),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "summarize_real_paper_snapshot.py"),
            "--output-json",
            str(output_json),
            "--verify-source-hashes",
        ],
        cwd=ROOT,
        check=True,
    )

    _write(root / "aggregate_summary.json", {**_aggregate(), "n_runs": 3})
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "summarize_real_paper_snapshot.py"),
            "--output-json",
            str(output_json),
            "--verify-source-hashes",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "Source hash verification failed" in completed.stderr + completed.stdout
    assert "aggregate" in completed.stderr + completed.stdout


def test_stale_outputs_detects_missing_and_mismatched_files(tmp_path):
    matching = tmp_path / "matching.txt"
    stale = tmp_path / "stale.txt"
    missing = tmp_path / "missing.txt"
    matching.write_text("expected\n", encoding="utf-8")
    stale.write_text("old\n", encoding="utf-8")

    assert _stale_outputs(
        {
            matching: "expected\n",
            stale: "new\n",
            missing: "new\n",
        }
    ) == [stale, missing]


def test_checked_in_real_paper_snapshot_is_current(monkeypatch):
    monkeypatch.chdir(ROOT)
    root = pathlib.Path("results") / "real_paper_v2"
    snapshot = build_snapshot(root)

    assert (root / "snapshot_summary.json").read_text(encoding="utf-8") == (
        json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n"
    )
    assert (root / "snapshot_summary.md").read_text(encoding="utf-8") == format_markdown(snapshot)


def _write(path: pathlib.Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_snapshot_inputs(root: pathlib.Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _write(root / "aggregate_summary.json", _aggregate())
    _write(root / "budget_curve.json", _budget())
    _write(root / "exactness_gap.json", _exactness())
    _write(root / "quality_summary.json", _quality())
    _write(root / "semantic_drift.json", _semantic())
    _write(root / "strict_replay.json", _strict())
    _write(root / "strict_replay_casebook.json", _casebook())
    _write(root / "strict_replay_paired.json", _paired())
    _write(root / "trace_taxonomy.json", _trace())


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


def _budget() -> dict:
    return {
        "policies": {
            "heuristic": _budget_policy(20, [(1, 0, 0), (2, 2, 0)]),
            "research": _budget_policy(20, [(1, 0, 0), (2, 12, 4), (3, 16, 5)]),
        }
    }


def _budget_policy(count, points) -> dict:
    budgets = [
        {
            "budget": budget,
            "count": count,
            "solved": solved,
            "exact": exact,
            "solve_rate": solved / count,
            "exact_rate": exact / count,
            "avg_checks_used": float(budget),
        }
        for budget, solved, exact in points
    ]
    previous = 0
    marginal = {}
    for budget, solved, _ in points:
        marginal[str(budget)] = solved - previous
        previous = solved
    return {
        "count": count,
        "max_observed_steps": points[-1][0],
        "budgets": budgets,
        "marginal_solves": marginal,
        "by_corruption": {
            "not_proposition": {
                "count": count,
                "budgets": budgets,
                "marginal_solves": marginal,
            }
        },
    }


def _exactness() -> dict:
    return {
        "policies": {
            "heuristic": _exactness_policy(20, 2, 0),
            "research": _exactness_policy(20, 16, 6),
        }
    }


def _exactness_policy(count, solved, exact) -> dict:
    return {
        "count": count,
        "solved": solved,
        "exact": exact,
        "solved_with_target": solved,
        "solved_not_exact": solved - exact,
        "solved_missing_target": 0,
        "solve_rate": solved / count,
        "exact_rate": exact / count,
        "exact_given_solved": exact / solved if solved else 0.0,
        "drift_given_solved": (solved - exact) / solved if solved else 0.0,
        "avg_header_similarity": 0.75 if solved else None,
        "avg_token_jaccard": 0.5 if solved else None,
        "by_corruption": {
            "not_proposition": {
                "count": count,
                "solved": solved,
                "exact": exact,
                "solved_not_exact": solved - exact,
                "solve_rate": solved / count,
                "exact_rate": exact / count,
                "exact_given_solved": exact / solved if solved else 0.0,
                "drift_given_solved": (solved - exact) / solved if solved else 0.0,
                "avg_header_similarity": 0.75 if solved else None,
                "avg_token_jaccard": 0.5 if solved else None,
            }
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


def _trace() -> dict:
    return {
        "policies": {
            "heuristic": _trace_policy(20, 2, 0, {"parse_error": 18, "solved": 2}),
            "research": _trace_policy(20, 16, 6, {"solved": 16, "parse_error": 4}),
        }
    }


def _trace_policy(count, solved, exact, terminal) -> dict:
    return {
        "count": count,
        "records_with_trace": count,
        "solved": solved,
        "exact": exact,
        "lean_ok_records": solved,
        "rejected_lean_ok_records": 0,
        "rejected_lean_ok_steps": 0,
        "accepted_after_rejection": 0,
        "solve_rate": solved / count,
        "exact_rate": exact / count,
        "lean_ok_rate": solved / count,
        "rejected_lean_ok_rate": 0.0,
        "avg_steps": 2.0,
        "median_steps": 2.0,
        "median_solve_step": 2.0 if solved else None,
        "avg_elapsed_ms": 12.0,
        "timeout_records": 0,
        "first_error_kind": {"parse_error": count},
        "terminal_error_kind": terminal,
        "acceptance_rejection_reasons": {},
        "failure_transitions": {"parse_error->parse_error": count - solved},
        "solved_by_step": {"2": solved} if solved else {},
        "by_corruption": {
            "not_proposition": {
                "count": count,
                "solved": solved,
                "exact": exact,
                "lean_ok_records": solved,
                "rejected_lean_ok_records": 0,
                "rejected_lean_ok_steps": 0,
                "accepted_after_rejection": 0,
                "solve_rate": solved / count,
                "exact_rate": exact / count,
                "lean_ok_rate": solved / count,
                "rejected_lean_ok_rate": 0.0,
                "avg_steps": 2.0,
                "avg_elapsed_ms": 12.0,
                "first_error_kind": {"parse_error": count},
                "terminal_error_kind": terminal,
                "failure_transitions": {"parse_error->parse_error": count - solved},
            }
        },
    }
