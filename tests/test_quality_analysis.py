import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

import quality_analysis as qa  # noqa: E402
from scripts import analyze_quality_summary as aqs  # noqa: E402


class QualityAnalysisTests(unittest.TestCase):
    def test_quality_summary_reports_nondegenerate_rate(self):
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
                        "exact": True,
                        "final_header": "theorem a (n : Nat) : n = n",
                        "target_header": "theorem a (n : Nat) : n = n",
                    },
                    {
                        "id": "b",
                        "corruption": "parse",
                        "ok": True,
                        "exact": False,
                        "final_header": "theorem b : True",
                        "target_header": "theorem b (n : Nat) : n = n",
                    },
                ],
            )

            summary = qa.analyze_root(root, ["heuristic"])
            pooled = summary["policies"]["heuristic"]["pooled"]

            self.assertEqual(pooled["count"], 2)
            self.assertEqual(pooled["solved"], 2)
            self.assertEqual(pooled["exact"], 1)
            self.assertEqual(pooled["degenerate_solved"], 1)
            self.assertEqual(pooled["nondegenerate_solved"], 1)
            self.assertAlmostEqual(pooled["nondegenerate_solved_rate"], 0.5)
            self.assertIn("parse", pooled["by_corruption"])
            self.assertIn("Quality-Adjusted Summary", qa.format_markdown(summary))

    def test_quality_summary_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            run_dir = root / "run_001"
            run_dir.mkdir()
            self._write_jsonl(
                run_dir / "research.jsonl",
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

            output_json = root / "quality.json"
            output_md = root / "quality.md"
            aqs.main(
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
            self.assertEqual(payload["policies"]["research"]["pooled"]["degenerate_solved"], 1)
            self.assertIn("Nondegenerate", output_md.read_text(encoding="utf-8"))

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
