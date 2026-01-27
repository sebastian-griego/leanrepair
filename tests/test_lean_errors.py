import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from lean_errors import parse_errors  # noqa: E402


class LeanErrorsTests(unittest.TestCase):
    def test_parse_errors_buckets(self):
        raw = "\n".join(
            [
                "/tmp/Main.lean:1:5: error: unknown identifier 'Foo'",
                "/tmp/Main.lean:2:3: error: failed to synthesize instance",
                "/tmp/Main.lean:3:7: error: type mismatch",
                "/tmp/Main.lean:4:9: error: unknown notation 'foo'",
                "/tmp/Main.lean:5:11: error: unexpected token",
                "/tmp/Main.lean:6:13: error: something else went wrong",
            ]
        )

        errors = parse_errors(raw)
        kinds = [err.kind for err in errors]
        self.assertEqual(
            kinds,
            [
                "unknown_identifier",
                "failed_typeclass",
                "type_mismatch",
                "notation_scope",
                "parse_error",
                "other",
            ],
        )


if __name__ == "__main__":
    unittest.main()
