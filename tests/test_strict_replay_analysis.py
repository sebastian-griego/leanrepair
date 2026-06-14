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
        self.assertEqual(summary["raw_degenerate_solved"], 0)

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
                ]
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["policies"]["research"]["raw_to_strict_loss"], 1)
            self.assertIn("Strict Replay Audit", output_md.read_text(encoding="utf-8"))

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
