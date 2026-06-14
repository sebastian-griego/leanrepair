import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

import strict_replay_analysis as sra  # noqa: E402
from scripts import analyze_strict_replay as asr  # noqa: E402


class StrictReplayAnalysisTests(unittest.TestCase):
    def test_strict_replay_rejects_degenerate_raw_acceptance(self):
        summary = sra.analyze_records(
            [
                {
                    "id": "a",
                    "policy": "research",
                    "corruption": "not_proposition",
                    "ok": True,
                    "final": "theorem a : True := by sorry",
                    "target": "theorem a (n : Nat) : n + 0 = n",
                    "trace": [
                        {
                            "ok": True,
                            "candidate": "theorem a : True := by sorry",
                        }
                    ],
                }
            ]
        )

        self.assertEqual(summary["raw_solved"], 1)
        self.assertEqual(summary["strict_solved"], 0)
        self.assertEqual(summary["raw_degenerate_solved"], 1)
        self.assertEqual(summary["raw_to_strict_loss"], 1)
        self.assertEqual(summary["discarded_degenerate_ok_steps"], 1)
        self.assertEqual(summary["raw_degenerate_reasons"]["goal_true"], 1)

    def test_strict_replay_accepts_later_exact_candidate(self):
        summary = sra.analyze_records(
            [
                {
                    "id": "b",
                    "policy": "research",
                    "corruption": "parse",
                    "ok": True,
                    "final": "theorem b (n : Nat) : n = n := by sorry",
                    "target": "theorem b (n : Nat) : n = n",
                    "trace": [
                        {
                            "ok": False,
                            "candidate": "theorem b (n : Nat : n = n := by sorry",
                        },
                        {
                            "ok": True,
                            "candidate": "theorem b (n : Nat) : n = n := by sorry",
                        },
                    ],
                }
            ]
        )

        self.assertEqual(summary["raw_solved"], 1)
        self.assertEqual(summary["strict_solved"], 1)
        self.assertEqual(summary["raw_exact"], 1)
        self.assertEqual(summary["strict_exact"], 1)
        self.assertEqual(summary["strict_not_exact"], 0)
        self.assertAlmostEqual(summary["strict_exact_given_strict"], 1.0)
        self.assertEqual(summary["raw_degenerate_solved"], 0)

    def test_strict_replay_reports_nondegenerate_nonexact_acceptance(self):
        summary = sra.analyze_records(
            [
                {
                    "id": "nonexact",
                    "policy": "research",
                    "corruption": "parse",
                    "ok": True,
                    "final": "theorem nonexact (n : Nat) : n = n + 0 := by sorry",
                    "target": "theorem nonexact (n : Nat) : n + 0 = n",
                    "trace": [
                        {
                            "ok": True,
                            "candidate": "theorem nonexact (n : Nat) : n = n + 0 := by sorry",
                        },
                    ],
                }
            ]
        )

        self.assertEqual(summary["strict_solved"], 1)
        self.assertEqual(summary["strict_exact"], 0)
        self.assertEqual(summary["strict_not_exact"], 1)
        self.assertAlmostEqual(summary["strict_exact_given_strict"], 0.0)
        self.assertEqual(summary["strict_nonexact_examples"][0]["id"], "nonexact")
        self.assertEqual(summary["by_corruption"]["parse"]["strict_not_exact"], 1)

    def test_strict_replay_rejects_bare_identifier_goal(self):
        summary = sra.analyze_records(
            [
                {
                    "id": "bare",
                    "policy": "research",
                    "corruption": "not_proposition",
                    "ok": True,
                    "final": "theorem bare (a b : Int) (b : Prop) : b := by sorry",
                    "target": "theorem bare (a b : Int) : (¬a ≤ b) = (b + 1 ≤ a)",
                    "trace": [
                        {
                            "ok": True,
                            "candidate": "theorem bare (a b : Int) (b : Prop) : b := by sorry",
                        },
                    ],
                }
            ]
        )

        self.assertEqual(summary["raw_solved"], 1)
        self.assertEqual(summary["strict_solved"], 0)
        self.assertEqual(summary["raw_degenerate_reasons"]["bare_identifier_goal"], 1)

    def test_strict_replay_can_recover_after_degenerate_trace_step(self):
        summary = sra.analyze_records(
            [
                {
                    "id": "c",
                    "policy": "research",
                    "corruption": "not_proposition",
                    "ok": True,
                    "final": "theorem c : True := by sorry",
                    "target": "theorem c (n : Nat) : n + 0 = n",
                    "trace": [
                        {
                            "ok": True,
                            "candidate": "theorem c : True := by sorry",
                        },
                        {
                            "ok": True,
                            "candidate": "theorem c (n : Nat) : n + 0 = n := by sorry",
                        },
                    ],
                }
            ]
        )

        self.assertEqual(summary["raw_solved"], 1)
        self.assertEqual(summary["strict_solved"], 1)
        self.assertEqual(summary["strict_exact"], 1)
        self.assertEqual(summary["raw_degenerate_solved"], 1)
        self.assertEqual(summary["raw_to_strict_loss"], 0)
        self.assertEqual(summary["recovered_after_degenerate"], 1)
        self.assertEqual(summary["changed_accepted_output"], 1)

    def test_replay_records_returns_row_level_decisions(self):
        rows = sra.replay_records(
            [
                {
                    "id": "loss",
                    "policy": "research",
                    "corruption": "not_proposition",
                    "ok": True,
                    "final": "theorem loss : True := by sorry",
                    "target": "theorem loss (n : Nat) : n = n",
                    "trace": [{"ok": True, "candidate": "theorem loss : True := by sorry"}],
                },
                {
                    "id": "strict",
                    "policy": "research",
                    "corruption": "parse",
                    "ok": True,
                    "final": "theorem strict (n : Nat) : n = n := by sorry",
                    "target": "theorem strict (n : Nat) : n = n",
                    "trace": [
                        {
                            "ok": True,
                            "candidate": "theorem strict (n : Nat) : n = n := by sorry",
                        }
                    ],
                },
            ]
        )

        by_id = {row["id"]: row for row in rows}
        self.assertTrue(by_id["loss"]["raw_ok"])
        self.assertFalse(by_id["loss"]["strict_ok"])
        self.assertEqual(by_id["loss"]["raw_reason"], "goal_true")
        self.assertTrue(by_id["strict"]["strict_ok"])
        self.assertTrue(by_id["strict"]["strict_exact"])

    def test_strict_replay_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            run_dir = root / "run_001"
            run_dir.mkdir()
            self._write_jsonl(
                run_dir / "research.jsonl",
                [
                    {
                        "id": "a",
                        "policy": "research",
                        "corruption": "parse",
                        "ok": True,
                        "final": "theorem a : True := by sorry",
                        "target": "theorem a (n : Nat) : n = n",
                        "trace": [
                            {
                                "ok": True,
                                "candidate": "theorem a : True := by sorry",
                            }
                        ],
                    }
                ],
            )

            output_json = root / "strict.json"
            output_md = root / "strict.md"
            output_records = root / "strict_records.jsonl"
            asr.main(
                [
                    "--root",
                    str(root),
                    "--policies",
                    "research",
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--output-records-jsonl",
                    str(output_records),
                ]
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            records = [
                json.loads(line)
                for line in output_records.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(payload["policies"]["research"]["raw_to_strict_loss"], 1)
            self.assertEqual(payload["policies"]["research"]["strict_not_exact"], 0)
            self.assertIn("Strict Replay Audit", output_md.read_text(encoding="utf-8"))
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["run"], "run_001")
            self.assertFalse(records[0]["strict_ok"])

    def test_replay_root_exports_all_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for run_name, record_id in [("run_001", "a"), ("run_002", "b")]:
                run_dir = root / run_name
                run_dir.mkdir()
                self._write_jsonl(
                    run_dir / "research.jsonl",
                    [
                        {
                            "id": record_id,
                            "corruption": "parse",
                            "ok": True,
                            "final": f"theorem {record_id} (n : Nat) : n = n := by sorry",
                            "target": f"theorem {record_id} (n : Nat) : n = n",
                            "trace": [
                                {
                                    "ok": True,
                                    "candidate": f"theorem {record_id} (n : Nat) : n = n := by sorry",
                                }
                            ],
                        }
                    ],
                )

            rows = sra.replay_root(root, ["research"])

            self.assertEqual([row["id"] for row in rows], ["a", "b"])
            self.assertEqual([row["run"] for row in rows], ["run_001", "run_002"])
            self.assertEqual({row["policy"] for row in rows}, {"research"})

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
