import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_body_compile_error_has_no_failure_section(self):
        rows = [row(f"k{i}", message="") for i in range(3)]
        body = autograder.render_body(self.scope, rows, [], "Foo.java:1: error")
        self.assertNotIn("## What failed", body)
        self.assertNotIn("<details>", body)
        self.assertNotIn("````text\n\n````", body)
        self.assertIn("# Loops: 0/6", body)

    def test_body_skips_failures_without_message(self):
        rows = [row("k0", message=""), row("k1", message="real")]
        body = autograder.render_body(self.scope, rows, [], None)
        self.assertNotIn("S.k0: 2 of 2", body)
        self.assertIn("S.k1: 2 of 2 assertions failed", body)
        body = autograder.render_body(self.scope, [row("k0", message="")], [], None)
        self.assertNotIn("## What failed", body)

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
                    # The compiler output replaces the per-koan failures.
                    self.assertNotIn("## What failed", body)

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


class MainFailureTest(unittest.TestCase):
    """main() against a fake JDK whose java misbehaves; no real Java runs."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        bundle = root / "bundle"
        for name in ("engine", "sensei"):
            (bundle / "src" / name).mkdir(parents=True)
            (bundle / "src" / name / "X.java").write_text("")
        shutil.copy(support.REPO / "classroom50/milestones.json", bundle / "milestones.json")
        (bundle / "koans.json").write_text(json.dumps([
            {"seriesClass": "AboutLoopsKoans", "series": "AboutLoops", "koan": "k", "assertions": 1}]))
        self.jdk = root / "jdk"
        (self.jdk / "bin").mkdir(parents=True)
        self.fake("javac", "exit 0")
        self.checkout = root / "checkout"
        (self.checkout / "src/main/java").mkdir(parents=True)
        env = {"CLASSROOM50_BUNDLE_DIR": str(bundle), "JAVA_HOME": str(self.jdk),
               "GITHUB_REF_NAME": "loops", "CLASSROOM": "c", "ASSIGNMENT": "a",
               "SUBMISSION_TAG": "submit/x", "COMMIT_URL": "u", "RELEASE_URL": "u"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        cwd = os.getcwd()
        os.chdir(self.checkout)
        self.addCleanup(os.chdir, cwd)

    def fake(self, tool, body):
        path = self.jdk / "bin" / tool
        path.write_text(f"#!/bin/sh\n{body}\n")
        path.chmod(0o755)

    def run_main(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = autograder.main()
        return code, err.getvalue()

    def assert_crash(self, needle):
        code, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn(needle, err)
        self.assertFalse((self.checkout / "result.json").exists())

    def test_grader_without_output(self):
        # argv: -cp <classes> engine.Grader <out.json> <series>...
        self.fake("java", "exit 0")
        self.assert_crash("no output")

    def test_grader_empty_output(self):
        self.fake("java", ': > "$4"')
        self.assert_crash("empty output")

    def test_grader_nonzero_exit(self):
        self.fake("java", "echo boom >&2; exit 3")
        self.assert_crash("exited with status 3")

    def test_grader_timeout(self):
        self.fake("java", "exec sleep 10")
        with mock.patch.object(autograder, "GRADER_TIMEOUT", 1):
            self.assert_crash("timed out")

    def test_unknown_ref(self):
        os.environ["GITHUB_REF_NAME"] = "nope"
        self.assert_crash("nope")

    def test_ref_from_github_ref(self):
        del os.environ["GITHUB_REF_NAME"]
        os.environ["GITHUB_REF"] = "refs/tags/loops"
        self.fake("java", "exit 0")
        self.assert_crash("no output")  # got past scope resolution


if __name__ == "__main__":
    unittest.main()
