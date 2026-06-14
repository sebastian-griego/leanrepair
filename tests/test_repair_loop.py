import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

import lean_check as lc  # noqa: E402
import acceptance  # noqa: E402
from lean_errors import ErrorInfo  # noqa: E402
import repair_loop as rl  # noqa: E402


class RepairLoopTests(unittest.TestCase):
    def test_unknown_identifier_repaired(self):
        def fake_lean_check(ctx: str, theorem: str, timeout_s: float) -> lc.CheckResult:
            if "(x : Type)" in theorem or "(x : Prop)" in theorem:
                return lc.CheckResult(ok=True, errors=[], raw="", elapsed_ms=1, timed_out=False)
            errors = [ErrorInfo(message="unknown identifier 'x'", kind="unknown_identifier")]
            return lc.CheckResult(ok=False, errors=errors, raw="", elapsed_ms=1, timed_out=False)

        with mock.patch.object(rl.lc, "lean_check", fake_lean_check):
            trace = rl.repair_one(
                nl="",
                ctx="",
                candidate0="theorem t : x",
                Tmax=3,
                timeout_s=1.0,
                policy=rl.default_policy,
            )

        self.assertGreaterEqual(len(trace.steps), 2)
        self.assertTrue(trace.steps[-1].result.ok)
        self.assertTrue("(x : Type)" in trace.steps[-1].candidate or "(x : Prop)" in trace.steps[-1].candidate)
        self.assertTrue(trace.accepted)

    def test_repeated_candidate_terminates(self):
        def fake_lean_check(ctx: str, theorem: str, timeout_s: float) -> lc.CheckResult:
            errors = [ErrorInfo(message="unknown identifier 'x'", kind="unknown_identifier")]
            return lc.CheckResult(ok=False, errors=errors, raw="", elapsed_ms=1, timed_out=False)

        def same_policy(nl: str, ctx: str, candidate: str, result: lc.CheckResult) -> str:
            return candidate

        with mock.patch.object(rl.lc, "lean_check", fake_lean_check):
            trace = rl.repair_one(
                nl="",
                ctx="",
                candidate0="theorem t : x",
                Tmax=5,
                timeout_s=1.0,
                policy=same_policy,
            )

        self.assertEqual(len(trace.steps), 1)

    def test_policy_can_return_multiple_candidates(self):
        def fake_lean_check(ctx: str, theorem: str, timeout_s: float) -> lc.CheckResult:
            if "(x : Type)" in theorem:
                return lc.CheckResult(ok=True, errors=[], raw="", elapsed_ms=1, timed_out=False)
            errors = [ErrorInfo(message="unknown identifier 'x'", kind="unknown_identifier")]
            return lc.CheckResult(ok=False, errors=errors, raw="", elapsed_ms=1, timed_out=False)

        def multi_policy(nl: str, ctx: str, candidate: str, result: lc.CheckResult):
            del nl, ctx, result
            return [
                candidate,
                "theorem t (x : Type) : x",
            ]

        with mock.patch.object(rl.lc, "lean_check", fake_lean_check):
            trace = rl.repair_one(
                nl="",
                ctx="",
                candidate0="theorem t : x",
                Tmax=4,
                timeout_s=1.0,
                policy=multi_policy,
            )

        self.assertTrue(trace.steps[-1].result.ok)
        self.assertIn("(x : Type)", trace.steps[-1].candidate)
        self.assertTrue(trace.steps[-1].accepted)

    def test_acceptance_can_reject_typechecked_candidate_and_continue(self):
        def fake_lean_check(ctx: str, theorem: str, timeout_s: float) -> lc.CheckResult:
            if "bad" in theorem:
                errors = [ErrorInfo(message="unknown identifier 'x'", kind="unknown_identifier")]
                return lc.CheckResult(ok=False, errors=errors, raw="", elapsed_ms=1, timed_out=False)
            return lc.CheckResult(ok=True, errors=[], raw="", elapsed_ms=1, timed_out=False)

        def multi_policy(nl: str, ctx: str, candidate: str, result: lc.CheckResult):
            del nl, ctx, candidate, result
            return [
                "theorem t : True",
                "theorem t (n : Nat) : n = n",
            ]

        def strictish_accept(candidate: str, result: lc.CheckResult):
            if not result.ok:
                return acceptance.AcceptanceDecision(False, "")
            if ": True" in candidate:
                return acceptance.AcceptanceDecision(False, "goal_true")
            return acceptance.AcceptanceDecision(True, "exact")

        with mock.patch.object(rl.lc, "lean_check", fake_lean_check):
            trace = rl.repair_one(
                nl="",
                ctx="",
                candidate0="theorem bad : x",
                Tmax=4,
                timeout_s=1.0,
                policy=multi_policy,
                accept=strictish_accept,
            )

        self.assertEqual(len(trace.steps), 3)
        self.assertTrue(trace.steps[1].result.ok)
        self.assertFalse(trace.steps[1].accepted)
        self.assertEqual(trace.steps[1].acceptance_reason, "goal_true")
        self.assertTrue(trace.accepted)
        self.assertEqual(trace.final_step, trace.steps[2])


if __name__ == "__main__":
    unittest.main()
