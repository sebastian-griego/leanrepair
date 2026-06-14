import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "src"))

import lean_check as lc  # noqa: E402
import repair_cli as rc  # noqa: E402
from llm_policy import ResearchHeuristicPolicy  # noqa: E402


class RepairCLITests(unittest.TestCase):
    def test_cli_smoke(self):
        input_path = ROOT / "tests" / "data" / "sample.jsonl"
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            output_path = tmp.name

        def fake_lean_check(ctx: str, theorem: str, timeout_s: float) -> lc.CheckResult:
            return lc.CheckResult(ok=True, errors=[], raw="", elapsed_ms=1, timed_out=False)

        with mock.patch.object(rc.rl.lc, "lean_check", fake_lean_check):
            rc.main(["--input", str(input_path), "--output", output_path, "--Tmax", "2"])

        with open(output_path, "r", encoding="utf-8") as handle:
            lines = [line.strip() for line in handle.readlines() if line.strip()]

        self.assertEqual(len(lines), 3)
        for line in lines:
            record = json.loads(line)
            self.assertIn("id", record)
            self.assertIn("ok", record)
            self.assertIn("final", record)
            self.assertIn("steps", record)
            self.assertIn("trace", record)
            self.assertIsInstance(record["trace"], list)
            self.assertIsInstance(record["steps"], int)

    def test_make_policy_supports_research_strict(self):
        policy = rc._make_policy("research_strict")

        self.assertIsInstance(policy, ResearchHeuristicPolicy)
        self.assertFalse(policy.allow_degenerate_fallbacks)


if __name__ == "__main__":
    unittest.main()
