import json
import unittest
from pathlib import Path

from classroom50 import autograder
from classroom50.autograder import Scope
from classroom50.tests import support

M = support.MILESTONES
MAIN = [m["series"] for m in M if not m["bonus"]]


def row(koan, assertions=2, passed=False, message="boom", series="S", failed=None):
    if failed is None:
        failed = 0 if passed else assertions
    return {"seriesClass": "S" + "Koans", "series": series, "koan": koan,
            "assertions": assertions, "failedAssertions": failed,
            "passed": passed, "message": message}


class ScopeTest(unittest.TestCase):
    def test_scope_milestone(self):
        self.assertEqual(autograder.resolve_scope("loops", M),
                         Scope("loops", ["AboutLoopsKoans"], []))

    def test_scope_submit(self):
        s = autograder.resolve_scope("submit/2026-10-29T00-00-00Z-abc1234", M)
        self.assertEqual(s.label, "Full course")
        self.assertEqual(len(s.scored), 9)
        self.assertEqual(s.scored, MAIN)
        self.assertEqual(s.bonus, ["AboutArraysKoans", "AboutInterfacesKoans"])

    def test_scope_unknown(self):
        with self.assertRaises(ValueError):
            autograder.resolve_scope("nope", M)

    def test_load_milestones(self):
        path = Path(support.REPO) / "classroom50/milestones.json"
        self.assertEqual(autograder.load_milestones(path), M)


class ResultTest(unittest.TestCase):
    def test_result_scores(self):
        env = {"CLASSROOM": "c", "ASSIGNMENT": "a", "SUBMISSION": "s",
               "COMMIT": "abc", "RELEASE": "r", "COMMIT_URL": "http://commit"}
        rows = [row("a", 3, True, ""), row("b", 2, False)]
        r = autograder.build_result(env, rows)
        self.assertEqual(r["score"], 3)
        self.assertEqual(r["max-score"], 5)
        self.assertEqual([t["test-name"] for t in r["tests"]], ["S.a", "S.b"])
        self.assertEqual([t["score"] for t in r["tests"]], [3, 0])
        self.assertEqual(r["review"], "http://commit")
        self.assertNotIn("owner", r)
        self.assertNotIn("assignment_type", r)
        json.dumps(r)

    def test_result_review_url_preferred(self):
        r = autograder.build_result({"REVIEW_URL": "http://r", "COMMIT_URL": "http://c"}, [])
        self.assertEqual(r["review"], "http://r")

    def test_failed_rows(self):
        manifest = [
            {"seriesClass": "AboutLoopsKoans", "series": "Loops", "koan": "k1", "assertions": 4},
            {"seriesClass": "AboutLoopsKoans", "series": "Loops", "koan": "k2", "assertions": 1},
            {"seriesClass": "AboutMethodsKoans", "series": "Methods", "koan": "k3", "assertions": 2},
        ]
        out = autograder.failed_rows(manifest, ["AboutLoopsKoans"])
        self.assertEqual(len(out), 2)
        for o in out:
            self.assertFalse(o["passed"])
            self.assertEqual(o["failedAssertions"], o["assertions"])
            self.assertEqual(o["message"], "")


class BodyTest(unittest.TestCase):
    scope = Scope("Loops", ["AboutLoopsKoans"], [])

    def test_body_lists_every_failure(self):
        rows = [row(f"k{i}") for i in range(3)]
        body = autograder.render_body(self.scope, rows, [], None)
        self.assertIn("# Loops: 0/6", body)
        pos = [body.index(f"S.k{i}: 2 of 2 assertions failed") for i in range(3)]
        self.assertEqual(pos, sorted(pos))

    def test_body_compile_error(self):
        out = "\n".join(f"line{i}" for i in range(1, 101))
        body = autograder.render_body(self.scope, [row("k")], [], out)
        self.assertIn("## Your code doesn't compile", body)
        self.assertIn("line40", body)
        self.assertNotIn("line41", body)

    def test_body_bonus_table(self):
        bonus = [row("BonusKoan", series="B", passed=True, message="")]
        body = autograder.render_body(self.scope, [row("k")], bonus, None)
        self.assertIn("## Bonus", body)
        koans = body.split("## Koans")[1].split("## ")[0]
        self.assertNotIn("BonusKoan", koans)

    def test_body_capped(self):
        rows = [row(f"k{i}", message="x" * 5000) for i in range(200)]
        body = autograder.render_body(self.scope, rows, [], None)
        self.assertLessEqual(len(body), autograder.BODY_LIMIT)
        self.assertTrue(body.endswith("_Report truncated; see the grade log for the full output._"))
        self.assertIn("<details>", body)
        self.assertNotIn("x" * (autograder.MESSAGE_LIMIT + 1), body)
        self.assertIn("\n... (truncated)", body)
        self.assertEqual(body.count("<details>"), body.count("</details>"))

    def test_body_capped_with_long_compile_lines(self):
        cases = {
            "one huge line": "y" * 500_000,
            "40 long lines": "\n".join("z" * 5000 for _ in range(40)),
            "huge backtick line": "`" * 500_000,
        }
        for name, out in cases.items():
            for with_failures in (False, True):
                rows = [row(f"k{i}", message="x" * 5000) for i in range(200)] if with_failures else [row("k")]
                with self.subTest(case=name, failures=with_failures):
                    body = autograder.render_body(self.scope, rows, [row("B", series="B", passed=True)], out)
                    self.assertLessEqual(len(body), autograder.BODY_LIMIT)
                    self.assertIn("## Your code doesn't compile", body)
                    self.assertIn("## Bonus", body)
                    if with_failures:
                        self.assertTrue(body.endswith("full output._"))

    def test_message_fence_safe(self):
        msg = "before ``` mid ````` </details> after"
        bonus = [row("BonusKoan", series="B", passed=True, message="")]
        body = autograder.render_body(self.scope, [row("k", message=msg)], bonus, None)
        self.assertEqual(body.count("## Bonus"), 1)
        i = body.index(msg)
        opening = body[:i].rstrip("\n").splitlines()[-1]
        closing = body[i + len(msg):].lstrip("\n").splitlines()[0]
        self.assertEqual(opening, "``````text")
        self.assertEqual(closing, "``````")

    def test_message_fence_min_four(self):
        body = autograder.render_body(self.scope, [row("k", message="plain")], [], None)
        self.assertIn("````text\nplain\n````\n", body)


if __name__ == "__main__":
    unittest.main()
