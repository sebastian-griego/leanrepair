import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

import semantic_drift_analysis as sda  # noqa: E402
from scripts import analyze_semantic_drift as asd  # noqa: E402


class SemanticDriftAnalysisTests(unittest.TestCase):
    def test_analyze_records_counts_degenerate_solved_outputs(self):
        records = [
            {
                "id": "exact",
                "corruption": "parse",
                "ok": True,
                "exact": True,
                "final_header": "theorem exact (n : Nat) : n = n",
                "target_header": "theorem exact (n : Nat) : n = n",
            },
            {
                "id": "true",
                "corruption": "parse",
                "ok": True,
                "exact": False,
                "final_header": "theorem true_case : True",
                "target_header": "theorem true_case (n : Nat) : n + 0 = n",
            },
            {
                "id": "refl",
                "corruption": "not_proposition",
                "ok": True,
                "exact": False,
                "final_header": "theorem refl_case : Nat = Nat",
                "target_header": "theorem refl_case (n : Nat) : n + 0 = n",
            },
            {
                "id": "unsolved",
                "corruption": "type_mismatch",
                "ok": False,
                "exact": False,
                "final_header": "theorem unsolved : Nat",
                "target_header": "theorem unsolved : 0 = 0",
            },
        ]

        summary = sda.analyze_records(records)

        self.assertEqual(summary["count"], 4)
        self.assertEqual(summary["solved"], 3)
        self.assertEqual(summary["exact"], 1)
        self.assertEqual(summary["degenerate_solved"], 2)
        self.assertEqual(summary["nondegenerate_solved"], 1)
        self.assertEqual(summary["degenerate_reasons"]["goal_true"], 1)
        self.assertEqual(summary["degenerate_reasons"]["reflexive_equality"], 1)
        self.assertEqual(summary["by_corruption"]["parse"]["degenerate_solved"], 1)

    def test_low_token_recall_is_counted_when_not_otherwise_trivial(self):
        summary = sda.analyze_records(
            [
                {
                    "id": "low",
                    "corruption": "unknown_type_symbol",
                    "ok": True,
                    "exact": False,
                    "final_header": "theorem low : 0 < 1",
                    "target_header": "theorem low (n : Nat) : n + 0 = n",
                }
            ],
            token_recall_floor=0.5,
        )

        self.assertEqual(summary["degenerate_solved"], 1)
        self.assertEqual(summary["degenerate_reasons"]["low_target_token_recall"], 1)

    def test_semantic_drift_cli_writes_outputs(self):
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
                        "target_header": "theorem a (n : Nat) : n = n",
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
                        "final_header": "theorem a (n : Nat) : n = n",
                        "target_header": "theorem a (n : Nat) : n = n",
                    }
                ],
            )

            output_json = root / "semantic.json"
            output_md = root / "semantic.md"
            asd.main(
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
            self.assertEqual(payload["policies"]["heuristic"]["degenerate_solved"], 1)
            self.assertEqual(payload["policies"]["research"]["exact"], 1)
            self.assertIn("Semantic Drift Audit", output_md.read_text(encoding="utf-8"))

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
