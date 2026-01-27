import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

import lean_check as lc  # noqa: E402


class LeanCheckTests(unittest.TestCase):
    def test_rejects_forbidden_keywords(self):
        forbidden_snippets = [
            "import Mathlib",
            "open Foo",
            "namespace Bar",
            "section",
            "macro",
            "syntax",
            "#eval 1",
            "#reduce 1",
            "set_option pp.universes true",
            "attribute [simp] Foo",
            "inductive Foo",
            "structure Bar",
            "class C",
            "instance inst : C",
            "`backtick`",
        ]

        for snippet in forbidden_snippets:
            candidate = f"theorem t : True\n{snippet}"
            self.assertIsNone(lc.sanitize_candidate(candidate))

    def test_accepts_minimal_theorem(self):
        candidate = "theorem t : True := by sorry"
        sanitized = lc.sanitize_candidate(candidate)
        self.assertEqual(sanitized, "theorem t : True")
        built = lc.build_theorem(sanitized)
        self.assertEqual(built, "theorem t : True := by sorry")

    def test_lean_check_unknown_identifier(self):
        lc._CACHE.clear()

        def fake_run_lean(file_contents: str, timeout_s: float):
            raw = "/tmp/Main.lean:1:12: error: unknown identifier 'Foo'"
            return raw, 5, False, 1

        with mock.patch.object(lc, "_run_lean", fake_run_lean):
            result = lc.lean_check("", "theorem t : Foo := by sorry", 1.0)

        self.assertFalse(result.ok)
        self.assertTrue(result.errors)
        self.assertIn("unknown identifier", result.errors[0].message)

    def test_timeout_path(self):
        lc._CACHE.clear()

        def fake_run_lean(file_contents: str, timeout_s: float):
            return "", 1000, True, None

        with mock.patch.object(lc, "_run_lean", fake_run_lean):
            result = lc.lean_check("", "theorem t : True := by sorry", 0.01)

        self.assertFalse(result.ok)
        self.assertTrue(result.timed_out)


if __name__ == "__main__":
    unittest.main()
