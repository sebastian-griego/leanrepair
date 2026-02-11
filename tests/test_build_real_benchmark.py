import pathlib
import random
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "scripts"))

import build_real_benchmark as rb  # noqa: E402


class BuildRealBenchmarkTests(unittest.TestCase):
    def test_extract_header_from_line(self):
        line = "theorem foo (n : Nat) : n = n := by simp"
        self.assertEqual(rb._extract_header_from_line(line), "theorem foo (n : Nat) : n = n")

    def test_extract_header_rejects_comment_and_where(self):
        self.assertIsNone(rb._extract_header_from_line("-- theorem nope : True"))
        self.assertIsNone(rb._extract_header_from_line("theorem foo : True where"))

    def test_rename_decl(self):
        header = "theorem foo (n : Nat) : n = n"
        renamed = rb._rename_decl(header, "bar")
        self.assertEqual(renamed, "theorem bar (n : Nat) : n = n")

    def test_corrupt_parse_missing_colon(self):
        header = "theorem foo (n : Nat) : n = n"
        corrupted = rb._corrupt_parse_missing_colon(header, random.Random(0))
        self.assertNotIn(") :", corrupted)
        self.assertIn(")   n", corrupted)

    def test_corrupt_not_proposition_uses_binder_name(self):
        header = "theorem foo (n : Nat) (m : Nat) : n = m"
        corrupted = rb._corrupt_not_proposition(header, random.Random(0))
        self.assertTrue(corrupted.endswith(": m") or corrupted.endswith(": n"))


if __name__ == "__main__":
    unittest.main()
