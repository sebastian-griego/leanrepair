import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

import exactness_analysis as ea  # noqa: E402
from scripts import analyze_exactness_gap as aeg  # noqa: E402


class ExactnessAnalysisTests(unittest.TestCase):
    def test_analyze_records_separates_solved_exact_and_drift(self):
        records = [
            {
                "id": "a",
                "corruption": "parse",
                "ok": True,
                "exact": True,
                "final_header": "theorem a : True",
                "target_header": "theorem a : True",
            },
            {
                "id": "b",
                "corruption": "parse",
                "ok": True,
                "exact": False,
                "final_header": "theorem b : True",
                "target_header": "theorem b : False",
            },
            {
                "id": "c",
                "corruption": "name",
                "ok": False,
                "exact": False,
                "final_header": "theorem c : True",
                "target_header": "theorem c : True",
            },
        ]

        summary = ea.analyze_records(records, max_examples=5)

        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["solved"], 2)
        self.assertEqual(summary["exact"], 1)
        self.assertEqual(summary["solved_not_exact"], 1)
        self.assertAlmostEqual(summary["exact_given_solved"], 0.5)
        self.assertEqual(summary["by_corruption"]["parse"]["solved_not_exact"], 1)
        self.assertEqual(summary["drift_examples"][0]["id"], "b")

    def test_solved_record_without_target_is_not_exact(self):
        summary = ea.analyze_records(
            [
                {
                    "id": "a",
                    "corruption": "unknown",
                    "ok": True,
                    "exact": True,
                    "final_header": "theorem a : True",
                }
            ]
        )

        self.assertEqual(summary["solved"], 1)
        self.assertEqual(summary["exact"], 0)
        self.assertEqual(summary["solved_missing_target"], 1)
        self.assertEqual(summary["exact_given_solved"], 0.0)

    def test_exactness_gap_cli_writes_outputs(self):
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
                        "ok": True,
                        "exact": False,
                        "final_header": "theorem a : True",
                        "target_header": "theorem a : False",
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
                        "final_header": "theorem a : False",
                        "target_header": "theorem a : False",
                    }
                ],
            )

            output_json = root / "exactness.json"
            output_md = root / "exactness.md"
            aeg.main(
                [
                    "--root",
                    str(root),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ]
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["policies"]["heuristic"]["solved_not_exact"], 1)
            self.assertEqual(payload["policies"]["research"]["exact"], 1)
            self.assertIn("Exactness Gap", output_md.read_text(encoding="utf-8"))

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
