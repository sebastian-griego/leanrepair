import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

import lean_check as lc  # noqa: E402
from lean_errors import ErrorInfo  # noqa: E402
from llm_policy import HeuristicPolicy  # noqa: E402


class LLMPolicyTests(unittest.TestCase):
    def test_heuristic_policy_integration(self):
        policy = HeuristicPolicy()
        result = lc.CheckResult(
            ok=False,
            errors=[ErrorInfo(message="unknown identifier 'x'", kind="unknown_identifier")],
            raw="",
            elapsed_ms=0,
            timed_out=False,
        )
        output = policy.propose("", "", "theorem t : x", result)
        self.assertIn("(x : Type)", output)


if __name__ == "__main__":
    unittest.main()
