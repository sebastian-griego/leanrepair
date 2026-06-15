import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

from jsonl_io import JsonlError  # noqa: E402
import strict_replay_casebook as srcb  # noqa: E402
from scripts import analyze_strict_replay_casebook as cli  # noqa: E402
from scripts import run_experiments as rex  # noqa: E402


class StrictReplayCasebookTests(unittest.TestCase):
    def test_casebook_counts_loss_nonexact_and_recovery_flags(self):
        summary = srcb.analyze_records(
            [
                self._strict_row(
                    "run_001",
                    "loss",
                    "research",
                    corruption="not_proposition",
                    strict_ok=False,
                    strict_exact=False,
                    raw_reason="goal_true",
                ),
                self._strict_row(
                    "run_001",
                    "nonexact",
                    "research",
                    strict_ok=True,
                    strict_exact=False,
                    target_header="theorem nonexact : n + 0 = n",
                ),
                self._strict_row(
                    "run_001",
                    "recovered",
                    "research",
                    corruption="type_mismatch",
                    raw_reason="reflexive_equality",
                    recovered_after_degenerate=True,
                    changed_accepted_output=True,
                    strict_final_header="theorem recovered (n : Nat) : n = n",
                    strict_final_goal="n = n",
                    discarded_degenerate_ok_steps=1,
                ),
                self._strict_row("run_001", "exact", "heuristic"),
                self._strict_row(
                    "run_001",
                    "unsolved",
                    "heuristic",
                    raw_ok=False,
                    strict_ok=False,
                    strict_exact=False,
                ),
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

    def test_analyze_records_validates_in_memory_schema(self):
        row = self._strict_row("run_001", "bad", "research")
        del row["reported_ok"]

        with self.assertRaises(JsonlError) as ctx:
            srcb.analyze_records([row])

        self.assertIn(
            "missing reported_ok at input strict replay records:1",
            str(ctx.exception),
        )

    def test_analyze_records_rejects_duplicate_in_memory_keys(self):
        rows = [
            self._strict_row("run_001", "dup", "research"),
            self._strict_row("run_001", "dup", "research"),
        ]

        with self.assertRaises(JsonlError) as ctx:
            srcb.analyze_records(rows)

        message = str(ctx.exception)
        self.assertIn(
            "duplicate strict replay row run='run_001', id='dup', policy='research'",
            message,
        )
        self.assertIn("at input row 2", message)
        self.assertIn("first seen at input row 1", message)

    def test_cli_writes_casebook_outputs_from_records_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            records = root / "strict_replay_records.jsonl"
            self._write_jsonl(
                records,
                [
                    self._strict_row(
                        "run_001",
                        "loss",
                        "research",
                        corruption="not_proposition",
                        strict_ok=False,
                        strict_exact=False,
                        raw_reason="goal_true",
                    ),
                    self._strict_row(
                        "run_001",
                        "nonexact",
                        "research",
                        strict_ok=True,
                        strict_exact=False,
                    ),
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

    def test_run_experiments_strict_replay_writer_emits_casebook(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            self._write_jsonl(
                run_dir / "research.jsonl",
                [
                    {
                        "id": "loss",
                        "policy": "research",
                        "corruption": "not_proposition",
                        "ok": True,
                        "final": "theorem loss : True := by sorry",
                        "target": "theorem loss (n : Nat) : n = n",
                        "trace": [
                            {
                                "ok": True,
                                "candidate": "theorem loss : True := by sorry",
                            }
                        ],
                    }
                ],
            )

            rex._write_strict_replay(run_dir, ["research"])

            self.assertTrue((run_dir / "strict_replay.json").exists())
            self.assertTrue((run_dir / "strict_replay.md").exists())
            self.assertTrue((run_dir / "strict_replay_records.jsonl").exists())
            self.assertTrue((run_dir / "strict_replay_casebook.json").exists())
            self.assertTrue((run_dir / "strict_replay_casebook.md").exists())
            self.assertTrue((run_dir / "strict_replay_casebook_cases.jsonl").exists())
            casebook = json.loads((run_dir / "strict_replay_casebook.json").read_text(encoding="utf-8"))
            self.assertEqual(casebook["dataset"]["focused_cases"], 1)
            self.assertEqual(casebook["primary_case_counts"]["raw_to_strict_loss"], 1)

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )

    def _strict_row(
        self,
        run: str,
        item_id: str,
        policy: str,
        *,
        raw_ok: bool = True,
        strict_ok: bool = True,
        strict_exact: bool = True,
        raw_reason: str = "",
        corruption: str = "parse",
        recovered_after_degenerate: bool = False,
        changed_accepted_output: bool = False,
        strict_final_header: str | None = None,
        target_header: str | None = None,
        strict_final_goal: str | None = None,
        discarded_degenerate_ok_steps: int = 0,
    ) -> dict:
        return {
            "run": run,
            "id": item_id,
            "policy": policy,
            "corruption": corruption,
            "reported_ok": raw_ok,
            "raw_ok": raw_ok,
            "raw_exact": strict_exact,
            "raw_degenerate": bool(raw_reason),
            "raw_reason": raw_reason,
            "raw_step_index": 1 if raw_ok else None,
            "raw_final_header": f"theorem {item_id} : True" if raw_ok else "",
            "raw_final_goal": "True" if raw_ok else "",
            "target_header": target_header or f"theorem {item_id} : True",
            "target_goal": "True",
            "strict_ok": strict_ok,
            "strict_exact": strict_exact,
            "strict_step_index": 1 if strict_ok else None,
            "strict_final_header": strict_final_header
            if strict_final_header is not None
            else f"theorem {item_id} : True" if strict_ok else "",
            "strict_final_goal": strict_final_goal
            if strict_final_goal is not None
            else "True" if strict_ok else "",
            "discarded_degenerate_ok_steps": discarded_degenerate_ok_steps,
            "recovered_after_degenerate": recovered_after_degenerate,
            "changed_accepted_output": changed_accepted_output,
        }


if __name__ == "__main__":
    unittest.main()
