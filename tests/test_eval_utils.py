import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from eval_utils import ExperimentRecord, normalize_header, summarize, wilson_interval  # noqa: E402


class EvalUtilsTests(unittest.TestCase):
    def test_normalize_header(self):
        text = "theorem t : True := by sorry"
        self.assertEqual(normalize_header(text), "theorem t : True")

    def test_wilson_interval_bounds(self):
        lo, hi = wilson_interval(7, 10)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        self.assertLess(lo, hi)

    def test_summarize_exact_and_solved(self):
        records = [
            ExperimentRecord(
                item_id="a",
                policy="heuristic",
                corruption="parse",
                ok=True,
                steps=2,
                elapsed_ms=100,
                final="theorem a : True := by sorry",
                target="theorem a : True",
            ),
            ExperimentRecord(
                item_id="b",
                policy="heuristic",
                corruption="parse",
                ok=False,
                steps=3,
                elapsed_ms=300,
                final="theorem b : Nat := by sorry",
                target="theorem b : True",
            ),
        ]
        summary = summarize(records)
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["solved"], 1)
        self.assertAlmostEqual(summary["solve_rate"], 0.5)
        self.assertAlmostEqual(summary["exact_rate"], 0.5)
        self.assertIn("parse", summary["by_corruption"])


if __name__ == "__main__":
    unittest.main()
