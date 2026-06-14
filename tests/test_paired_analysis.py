import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts import analyze_paired_results as apr  # noqa: E402


class PairedAnalysisTests(unittest.TestCase):
    def test_paired_counts_include_effect_size_and_ci(self):
        pairs = [
            ({"ok": True, "exact": True}, {"ok": True, "exact": True}),
            ({"ok": True, "exact": False}, {"ok": False, "exact": False}),
            ({"ok": False, "exact": False}, {"ok": True, "exact": True}),
            ({"ok": False, "exact": False}, {"ok": False, "exact": False}),
        ]

        summary = apr._paired_counts(pairs, bootstrap_samples=100, seed=7)

        self.assertEqual(summary["both_solve"], 1)
        self.assertEqual(summary["policy_a_only"], 1)
        self.assertEqual(summary["policy_b_only"], 1)
        self.assertEqual(summary["neither_solve"], 1)
        self.assertAlmostEqual(summary["policy_b_solve_lift"], 0.0)
        self.assertAlmostEqual(summary["policy_b_exact_lift"], 0.25)
        self.assertEqual(len(summary["policy_b_solve_lift_ci95"]), 2)
        self.assertEqual(len(summary["policy_b_exact_lift_ci95"]), 2)

    def test_main_reports_unpaired_coverage_and_bootstrap_lifts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            run_dir = root / "run_001"
            run_dir.mkdir()
            self._write_jsonl(
                run_dir / "heuristic.jsonl",
                [
                    {"id": "a", "ok": True, "exact": True, "corruption": "case"},
                    {"id": "b", "ok": False, "exact": False, "corruption": "case"},
                    {"id": "only_a", "ok": True, "exact": False, "corruption": "case"},
                ],
            )
            self._write_jsonl(
                run_dir / "research.jsonl",
                [
                    {"id": "a", "ok": True, "exact": True, "corruption": "case"},
                    {"id": "b", "ok": True, "exact": False, "corruption": "case"},
                    {"id": "only_b", "ok": False, "exact": False, "corruption": "case"},
                ],
            )

            output_json = root / "paired.json"
            output_md = root / "paired.md"
            apr.main(
                [
                    "--root",
                    str(root),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--bootstrap-samples",
                    "100",
                    "--seed",
                    "11",
                ]
            )

            summary = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["coverage"]["policy_a_unpaired"], 1)
            self.assertEqual(summary["coverage"]["policy_b_unpaired"], 1)
            self.assertEqual(summary["coverage"]["paired_records"], 2)
            self.assertAlmostEqual(summary["pooled"]["policy_b_solve_lift"], 0.5)
            self.assertIn("policy_b_solve_lift_ci95", summary["pooled"])
            self.assertIn("## Coverage", output_md.read_text(encoding="utf-8"))

    def test_strict_pairs_fails_on_missing_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            run_dir = root / "run_001"
            run_dir.mkdir()
            self._write_jsonl(run_dir / "heuristic.jsonl", [{"id": "a", "ok": True}])
            self._write_jsonl(run_dir / "research.jsonl", [{"id": "b", "ok": True}])

            with self.assertRaises(SystemExit):
                apr.main(["--root", str(root), "--strict-pairs"])

    def _write_jsonl(self, path: pathlib.Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
