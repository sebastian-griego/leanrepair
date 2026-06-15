import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

from jsonl_io import JsonlError  # noqa: E402
import strict_replay_paired as srp  # noqa: E402
from scripts import analyze_strict_replay_paired as cli  # noqa: E402
from scripts import run_experiments as rex  # noqa: E402


class StrictReplayPairedTests(unittest.TestCase):
    def test_analyze_records_reports_strict_and_exact_lifts(self):
        summary = srp.analyze_records(
            [
                self._row("run_001", "b_win", "heuristic", raw_ok=True, strict_ok=False),
                self._row("run_001", "b_win", "research", raw_ok=True, strict_ok=True, strict_exact=True),
                self._row("run_001", "a_win", "heuristic", raw_ok=True, strict_ok=True),
                self._row("run_001", "a_win", "research", raw_ok=True, strict_ok=False),
                self._row("run_001", "raw_lost", "heuristic", raw_ok=False, strict_ok=False),
                self._row(
                    "run_001",
                    "raw_lost",
                    "research",
                    raw_ok=True,
                    strict_ok=False,
                    raw_degenerate=True,
                    raw_reason="goal_true",
                ),
                self._row(
                    "run_001",
                    "raw_lost_reflexive",
                    "heuristic",
                    raw_ok=False,
                    strict_ok=False,
                    corruption="type_mismatch",
                ),
                self._row(
                    "run_001",
                    "raw_lost_reflexive",
                    "research",
                    raw_ok=True,
                    strict_ok=False,
                    raw_degenerate=True,
                    raw_reason="reflexive_equality",
                    corruption="type_mismatch",
                ),
                self._row("run_001", "exact_win", "heuristic", raw_ok=True, strict_ok=True),
                self._row(
                    "run_001",
                    "exact_win",
                    "research",
                    raw_ok=True,
                    strict_ok=True,
                    strict_exact=True,
                ),
            ],
            max_cases=5,
        )
        markdown = srp.format_markdown(summary)

        self.assertEqual(summary["coverage"]["paired_records"], 5)
        self.assertEqual(summary["metrics"]["strict_ok"]["policy_a_only"], 1)
        self.assertEqual(summary["metrics"]["strict_ok"]["policy_b_only"], 1)
        self.assertEqual(summary["metrics"]["strict_exact"]["policy_b_only"], 2)
        self.assertEqual(summary["case_counts"]["policy_b_raw_wins_lost_by_strict"], 2)
        self.assertEqual(summary["raw_win_loss"]["total"], 2)
        self.assertEqual(
            {row["name"]: row["count"] for row in summary["raw_win_loss"]["by_reason"]},
            {"goal_true": 1, "reflexive_equality": 1},
        )
        self.assertEqual(
            {
                (row["reason"], row["corruption"]): row["count"]
                for row in summary["raw_win_loss"]["by_reason_and_corruption"]
            },
            {("goal_true", "parse"): 1, ("reflexive_equality", "type_mismatch"): 1},
        )
        self.assertEqual(summary["casebook"]["policy_b_strict_wins"][0]["id"], "b_win")
        self.assertIn("Strict Replay Paired Analysis", markdown)
        self.assertIn("Raw Wins Lost By Strict Replay Breakdown", markdown)
        self.assertIn("reflexive_equality", markdown)

    def test_analyze_records_validates_in_memory_schema(self):
        row = self._row("run_001", "bad", "research", raw_ok=True, strict_ok=True)
        del row["reported_ok"]

        with self.assertRaises(JsonlError) as ctx:
            srp.analyze_records([row])

        self.assertIn(
            "missing reported_ok at input strict replay records:1",
            str(ctx.exception),
        )

    def test_analyze_records_rejects_duplicate_in_memory_keys(self):
        rows = [
            self._row("run_001", "dup", "research", raw_ok=True, strict_ok=True),
            self._row("run_001", "dup", "research", raw_ok=True, strict_ok=True),
        ]

        with self.assertRaises(JsonlError) as ctx:
            srp.analyze_records(rows)

        message = str(ctx.exception)
        self.assertIn(
            "duplicate strict replay row run='run_001', id='dup', policy='research'",
            message,
        )
        self.assertIn("at input row 2", message)
        self.assertIn("first seen at input row 1", message)

    def test_cli_writes_paired_outputs_from_records_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            records = root / "strict_replay_records.jsonl"
            self._write_jsonl(
                records,
                [
                    self._row("run_001", "item", "heuristic", raw_ok=False, strict_ok=False),
                    self._row("run_001", "item", "research", raw_ok=True, strict_ok=True),
                ],
            )
            output_json = root / "paired.json"
            output_md = root / "paired.md"

            cli.main(
                [
                    "--records-jsonl",
                    str(records),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ]
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["metrics"]["strict_ok"]["policy_b_only"], 1)
            self.assertIn("Strict solve lift", output_md.read_text(encoding="utf-8"))

    def test_run_experiments_strict_replay_writer_emits_paired_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            target = "theorem item (n : Nat) : n = n"
            self._write_jsonl(
                run_dir / "heuristic.jsonl",
                [
                    {
                        "id": "item",
                        "policy": "heuristic",
                        "corruption": "parse",
                        "ok": False,
                        "final": "",
                        "target": target,
                        "trace": [{"ok": False, "candidate": "theorem item (n : Nat) : n = "}],
                    }
                ],
            )
            self._write_jsonl(
                run_dir / "research.jsonl",
                [
                    {
                        "id": "item",
                        "policy": "research",
                        "corruption": "parse",
                        "ok": True,
                        "final": target + " := by sorry",
                        "target": target,
                        "trace": [{"ok": True, "candidate": target + " := by sorry"}],
                    }
                ],
            )

            rex._write_strict_replay(run_dir, ["heuristic", "research"])

            self.assertTrue((run_dir / "strict_replay_paired.json").exists())
            self.assertTrue((run_dir / "strict_replay_paired.md").exists())
            paired = json.loads((run_dir / "strict_replay_paired.json").read_text(encoding="utf-8"))
            self.assertEqual(paired["metrics"]["strict_ok"]["policy_b_only"], 1)

    def _row(
        self,
        run: str,
        item_id: str,
        policy: str,
        *,
        raw_ok: bool,
        strict_ok: bool,
        strict_exact: bool = False,
        raw_degenerate: bool = False,
        raw_reason: str = "",
        corruption: str = "parse",
    ) -> dict:
        return {
            "run": run,
            "id": item_id,
            "policy": policy,
            "corruption": corruption,
            "reported_ok": raw_ok,
            "raw_ok": raw_ok,
            "raw_exact": strict_exact,
            "raw_degenerate": raw_degenerate,
            "raw_reason": raw_reason,
            "raw_step_index": 1 if raw_ok else None,
            "raw_final_header": f"theorem {item_id} : True" if raw_ok else "",
            "raw_final_goal": "True" if raw_ok else "",
            "target_header": f"theorem {item_id} : True",
            "target_goal": "True",
            "strict_ok": strict_ok,
            "strict_exact": strict_exact,
            "strict_step_index": 2 if strict_ok else None,
            "strict_final_header": f"theorem {item_id} : True" if strict_ok else "",
            "strict_final_goal": "True" if strict_ok else "",
            "discarded_degenerate_ok_steps": 1 if raw_degenerate else 0,
            "recovered_after_degenerate": False,
            "changed_accepted_output": False,
        }

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
