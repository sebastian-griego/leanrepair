import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

import strict_replay_casebook as srcb  # noqa: E402
from scripts import analyze_strict_replay_casebook as cli  # noqa: E402


class StrictReplayCasebookTests(unittest.TestCase):
    def test_casebook_counts_loss_nonexact_and_recovery_flags(self):
        summary = srcb.analyze_records(
            [
                {
                    "run": "run_001",
                    "id": "loss",
                    "policy": "research",
                    "corruption": "not_proposition",
                    "raw_ok": True,
                    "strict_ok": False,
                    "strict_exact": False,
                    "raw_reason": "goal_true",
                    "raw_step_index": 2,
                    "raw_final_goal": "True",
                    "target_goal": "n = n",
                },
                {
                    "run": "run_001",
                    "id": "nonexact",
                    "policy": "research",
                    "corruption": "parse",
                    "raw_ok": True,
                    "strict_ok": True,
                    "strict_exact": False,
                    "strict_step_index": 3,
                    "strict_final_header": "theorem nonexact : n = n + 0",
                    "target_header": "theorem nonexact : n + 0 = n",
                },
                {
                    "run": "run_001",
                    "id": "recovered",
                    "policy": "research",
                    "corruption": "type_mismatch",
                    "raw_ok": True,
                    "strict_ok": True,
                    "strict_exact": True,
                    "raw_reason": "reflexive_equality",
                    "raw_step_index": 1,
                    "strict_step_index": 4,
                    "recovered_after_degenerate": True,
                    "changed_accepted_output": True,
                    "strict_final_goal": "n = n",
                },
                {
                    "run": "run_001",
                    "id": "exact",
                    "policy": "heuristic",
                    "corruption": "parse",
                    "raw_ok": True,
                    "strict_ok": True,
                    "strict_exact": True,
                },
                {
                    "run": "run_001",
                    "id": "unsolved",
                    "policy": "heuristic",
                    "corruption": "parse",
                    "raw_ok": False,
                    "strict_ok": False,
                    "strict_exact": False,
                },
            ]
        )
        markdown = srcb.format_markdown(summary)

        self.assertEqual(summary["dataset"]["records"], 5)
        self.assertEqual(summary["dataset"]["focused_cases"], 3)
        self.assertEqual(summary["primary_case_counts"]["raw_to_strict_loss"], 1)
        self.assertEqual(summary["primary_case_counts"]["strict_nonexact_accept"], 1)
        self.assertEqual(summary["primary_case_counts"]["recovered_after_degenerate"], 1)
        self.assertEqual(summary["primary_case_counts"]["strict_exact_accept"], 1)
        self.assertEqual(summary["primary_case_counts"]["unsolved"], 1)
        self.assertEqual(summary["flag_counts"]["changed_accepted_output"], 1)
        self.assertEqual(summary["raw_loss_reasons"]["goal_true"], 1)
        self.assertEqual(summary["casebook"]["raw_to_strict_losses"][0]["id"], "loss")
        self.assertEqual(summary["casebook"]["strict_nonexact_accepts"][0]["id"], "nonexact")
        self.assertIn("Strict Replay Casebook", markdown)
        self.assertIn("Raw Solves Lost Under Strict Replay", markdown)

    def test_cli_writes_casebook_outputs_from_records_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            records = root / "strict_replay_records.jsonl"
            self._write_jsonl(
                records,
                [
                    {
                        "run": "run_001",
                        "id": "loss",
                        "policy": "research",
                        "corruption": "not_proposition",
                        "raw_ok": True,
                        "strict_ok": False,
                        "strict_exact": False,
                        "raw_reason": "goal_true",
                    },
                    {
                        "run": "run_001",
                        "id": "nonexact",
                        "policy": "research",
                        "corruption": "parse",
                        "raw_ok": True,
                        "strict_ok": True,
                        "strict_exact": False,
                    },
                ],
            )
            output_json = root / "casebook.json"
            output_md = root / "casebook.md"
            cases_jsonl = root / "cases.jsonl"

            cli.main(
                [
                    "--records-jsonl",
                    str(records),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--cases-jsonl",
                    str(cases_jsonl),
                ]
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            cases = [
                json.loads(line)
                for line in cases_jsonl.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(payload["dataset"]["focused_cases"], 2)
            self.assertEqual([case["id"] for case in cases], ["loss", "nonexact"])
            self.assertIn("Strict Replay Casebook", output_md.read_text(encoding="utf-8"))

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
