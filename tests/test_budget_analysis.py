import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

import budget_analysis as ba  # noqa: E402
from scripts import analyze_budget_curve as abc  # noqa: E402


class BudgetAnalysisTests(unittest.TestCase):
    def test_analyze_records_builds_cumulative_budget_curve(self):
        records = [
            {
                "id": "a",
                "corruption": "parse",
                "ok": True,
                "exact": True,
                "steps": 1,
                "trace": [{"ok": True}],
            },
            {
                "id": "b",
                "corruption": "parse",
                "ok": True,
                "exact": False,
                "steps": 3,
                "trace": [{"ok": False}, {"ok": False}, {"ok": True}],
            },
            {
                "id": "c",
                "corruption": "name",
                "ok": False,
                "exact": False,
                "steps": 3,
                "trace": [{"ok": False}, {"ok": False}, {"ok": False}],
            },
        ]

        summary = ba.analyze_records(records, max_budget=3)

        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["budgets"][0]["solved"], 1)
        self.assertEqual(summary["budgets"][1]["solved"], 1)
        self.assertEqual(summary["budgets"][2]["solved"], 2)
        self.assertEqual(summary["budgets"][2]["exact"], 1)
        self.assertEqual(summary["marginal_solves"], {"1": 1, "2": 0, "3": 1})
        self.assertEqual(summary["by_corruption"]["parse"]["budgets"][2]["solved"], 2)

    def test_budget_curve_cli_writes_outputs(self):
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
                        "steps": 2,
                        "trace": [{"ok": False}, {"ok": False}],
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
                        "trace": [{"ok": False}, {"ok": True}],
                    }
                ],
            )

            output_json = root / "budget.json"
            output_md = root / "budget.md"
            abc.main(
                [
                    "--root",
                    str(root),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--max-budget",
                    "2",
                ]
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["policies"]["research"]["budgets"][1]["solved"], 1)
            self.assertIn("Repair-Budget Curve", output_md.read_text(encoding="utf-8"))

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
