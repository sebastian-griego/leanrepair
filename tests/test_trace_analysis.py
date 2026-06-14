import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

import trace_analysis as ta  # noqa: E402
from scripts import analyze_trace_taxonomy as att  # noqa: E402


class TraceAnalysisTests(unittest.TestCase):
    def test_analyze_records_summarizes_errors_and_corruptions(self):
        records = [
            {
                "id": "a",
                "corruption": "parse",
                "ok": True,
                "exact": True,
                "steps": 1,
                "elapsed_ms": 10,
                "trace": [
                    {
                        "candidate": "theorem a : True",
                        "ok": True,
                        "errors": [],
                        "elapsed_ms": 10,
                    }
                ],
            },
            {
                "id": "b",
                "corruption": "name",
                "ok": False,
                "exact": False,
                "steps": 2,
                "elapsed_ms": 30,
                "trace": [
                    {
                        "candidate": "theorem b : x",
                        "ok": False,
                        "errors": [{"kind": "unknown_identifier", "message": "unknown identifier 'x'"}],
                        "elapsed_ms": 10,
                    },
                    {
                        "candidate": "theorem b (x : Type) : x",
                        "ok": False,
                        "errors": [{"kind": "not_proposition", "message": "not a proposition"}],
                        "elapsed_ms": 20,
                    },
                ],
            },
        ]

        summary = ta.analyze_records(records, max_examples=3)

        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["solved"], 1)
        self.assertAlmostEqual(summary["solve_rate"], 0.5)
        self.assertEqual(summary["terminal_error_kind"]["solved"], 1)
        self.assertEqual(summary["terminal_error_kind"]["not_proposition"], 1)
        self.assertEqual(summary["failure_transitions"]["unknown_identifier->not_proposition"], 1)
        self.assertEqual(summary["by_corruption"]["name"]["failure_transitions"]["unknown_identifier->not_proposition"], 1)
        self.assertEqual(summary["failure_examples"][0]["id"], "b")

    def test_trace_taxonomy_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            run_dir = root / "run_001"
            run_dir.mkdir()
            self._write_jsonl(
                run_dir / "heuristic.jsonl",
                [
                    {
                        "id": "a",
                        "corruption": "parse",
                        "ok": False,
                        "exact": False,
                        "steps": 1,
                        "trace": [
                            {
                                "ok": False,
                                "timed_out": True,
                                "errors": [{"kind": "other", "message": "timeout"}],
                            }
                        ],
                    }
                ],
            )
            self._write_jsonl(
                run_dir / "research.jsonl",
                [
                    {
                        "id": "a",
                        "corruption": "parse",
                        "ok": True,
                        "exact": True,
                        "steps": 2,
                        "trace": [
                            {
                                "ok": False,
                                "errors": [{"kind": "parse_error", "message": "bad syntax"}],
                            },
                            {"ok": True, "errors": []},
                        ],
                    }
                ],
            )

            output_json = root / "taxonomy.json"
            output_md = root / "taxonomy.md"
            att.main(
                [
                    "--root",
                    str(root),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--max-examples",
                    "5",
                ]
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["policies"]["heuristic"]["terminal_error_kind"]["timeout"], 1)
            self.assertEqual(payload["policies"]["research"]["solved"], 1)
            self.assertIn("LeanRepair Trace Taxonomy", output_md.read_text(encoding="utf-8"))

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
