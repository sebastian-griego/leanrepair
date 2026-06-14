import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

import lean_check as lc  # noqa: E402
import repair_loop as rl  # noqa: E402
from lean_errors import ErrorInfo  # noqa: E402
from llm_policy import (  # noqa: E402
    HeuristicPolicy,
    ResearchHeuristicPolicy,
    _extract_candidate,
    _insert_missing_goal_colon,
    _normalize_core_type_names,
)


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
        self.assertIn("(x : Prop)", output)

    def test_extract_candidate_plain_text(self):
        text = "theorem foo : Nat"
        self.assertEqual(_extract_candidate(text), "theorem foo : Nat")

    def test_extract_candidate_code_block(self):
        text = "```\ntheorem foo : Nat\n```"
        self.assertEqual(_extract_candidate(text), "theorem foo : Nat")

    def test_extract_candidate_language_tagged_block(self):
        text = "```lean\ntheorem foo : Nat\n```"
        self.assertEqual(_extract_candidate(text), "theorem foo : Nat")

    def test_extract_candidate_lean4_tagged_block(self):
        text = "```lean4\ntheorem bar (x : Nat) : Nat\n```"
        self.assertEqual(_extract_candidate(text), "theorem bar (x : Nat) : Nat")

    def test_extract_candidate_drops_imports_and_proof_body(self):
        text = """```lean
import Mathlib

theorem foo (n : Nat) : n = n := by
  rfl
```"""
        self.assertEqual(_extract_candidate(text), "theorem foo (n : Nat) : n = n")

    def test_extract_candidate_keeps_multiline_header(self):
        text = """Here is the repair:

```lean
lemma foo
    (n : Nat)
    : n = n := by
  rfl
```"""
        self.assertEqual(
            _extract_candidate(text),
            "lemma foo\n    (n : Nat)\n    : n = n",
        )

    def test_research_policy_returns_multiple_candidates(self):
        policy = ResearchHeuristicPolicy()
        result = lc.CheckResult(
            ok=False,
            errors=[ErrorInfo(message="unknown identifier 'x'", kind="unknown_identifier")],
            raw="",
            elapsed_ms=0,
            timed_out=False,
        )
        proposals = policy.propose_many("", "", "theorem t : x", result)
        self.assertGreaterEqual(len(proposals), 2)
        self.assertTrue(any("(x : Prop)" in p or "(x : Type)" in p for p in proposals))

    def test_research_policy_handles_not_proposition(self):
        policy = ResearchHeuristicPolicy()
        result = lc.CheckResult(
            ok=False,
            errors=[ErrorInfo(message="type of theorem 'u' is not a proposition", kind="not_proposition")],
            raw="",
            elapsed_ms=0,
            timed_out=False,
        )
        proposals = policy.propose_many("", "", "theorem u : x", result)
        self.assertTrue(any(": x = x" in p or ": True" in p for p in proposals))

    def test_research_strict_suppresses_degenerate_fallbacks(self):
        policy = ResearchHeuristicPolicy(allow_degenerate_fallbacks=False)
        result = lc.CheckResult(
            ok=False,
            errors=[ErrorInfo(message="type of theorem 'u' is not a proposition", kind="not_proposition")],
            raw="",
            elapsed_ms=0,
            timed_out=False,
        )
        proposals = policy.propose_many("", "", "theorem u : Nat", result)

        self.assertFalse(any(": True" in p for p in proposals))
        self.assertFalse(any(": Nat = Nat" in p for p in proposals))

    def test_research_strict_does_not_accept_trivial_not_prop_success(self):
        policy = ResearchHeuristicPolicy(allow_degenerate_fallbacks=False)

        def fake_lean_check(ctx: str, theorem: str, timeout_s: float) -> lc.CheckResult:
            del ctx, timeout_s
            if ": True" in theorem or ": Nat = Nat" in theorem:
                return lc.CheckResult(ok=True, errors=[], raw="", elapsed_ms=1, timed_out=False)
            return lc.CheckResult(
                ok=False,
                errors=[ErrorInfo(message="type of theorem 'u' is not a proposition", kind="not_proposition")],
                raw="",
                elapsed_ms=1,
                timed_out=False,
            )

        original = lc.lean_check
        try:
            lc.lean_check = fake_lean_check
            trace = rl.repair_one(
                nl="",
                ctx="",
                candidate0="theorem u : Nat",
                Tmax=4,
                timeout_s=1.0,
                policy=policy.propose_many,
            )
        finally:
            lc.lean_check = original

        self.assertEqual(len(trace.steps), 1)
        self.assertFalse(trace.steps[-1].result.ok)

    def test_insert_missing_colon_after_brace_binder(self):
        candidate = "theorem t {x : Nat} x = x"
        fixed = _insert_missing_goal_colon(candidate)
        self.assertEqual(fixed, "theorem t {x : Nat} : x = x")

    def test_insert_missing_colon_after_theorem_name(self):
        candidate = "theorem t True"
        fixed = _insert_missing_goal_colon(candidate)
        self.assertEqual(fixed, "theorem t : True")

    def test_normalize_core_type_names_uint_and_fields(self):
        candidate = "theorem t (x : uint64) : x.toint = x.tonat"
        fixed = _normalize_core_type_names(candidate)
        self.assertIn("UInt64", fixed)
        self.assertIn("toInt", fixed)
        self.assertIn("toNat", fixed)


if __name__ == "__main__":
    unittest.main()
