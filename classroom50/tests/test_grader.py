import subprocess
import tempfile
import unittest
from pathlib import Path

from classroom50.tests import support

SERIES = "AboutConsoleAndVariablesKoans"
# Koan name (title) of the koan that calls sayHelloInConsole, the first one in the series.
SAY_HELLO_KOAN = "Displaying some text in the console"


def build(kind, root, patch=None):
    checkout = support.make_checkout(kind, root / kind)
    if patch:
        patch(checkout / "src/main/java")
    classes = root / f"{kind}-classes"
    support.compile_with_grader(checkout / "src/main/java", classes)
    return classes


class GraderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.solved = build("solved", cls.root)
        cls.blank = build("blank", cls.root)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def out(self, name):
        return self.root / f"{self._testMethodName}-{name}.json"

    def test_solved_series_all_pass(self):
        rows = support.run_grader(self.solved, self.out("run"), SERIES)
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertTrue(row["passed"], row)
            self.assertEqual(row["failedAssertions"], 0)
            self.assertGreater(row["assertions"], 0)
            self.assertEqual(row["message"], "")
            self.assertEqual(row["series"], "AboutConsoleAndVariables")
            self.assertEqual(row["seriesClass"], SERIES)

    def test_blank_series_all_fail_with_message(self):
        rows = support.run_grader(self.blank, self.out("run"), SERIES)
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertFalse(row["passed"], row)
            self.assertEqual(row["failedAssertions"], row["assertions"])
            self.assertNotEqual(row["message"], "")
            self.assertNotIn("\x1b", row["message"])

    def test_list_mode_matches_run(self):
        series = [m["series"] for m in support.MILESTONES]
        listed = support.run_grader(self.solved, self.out("list"), "--list", *series)
        ran = support.run_grader(self.solved, self.out("run"), *series)
        key = lambda r: (r["seriesClass"], r["koan"], r["assertions"])
        self.assertEqual([key(r) for r in listed], [key(r) for r in ran])
        self.assertEqual(len(listed), 81)
        for row in listed:
            self.assertEqual(set(row), {"seriesClass", "series", "koan", "assertions"})

    def test_unknown_series_fails(self):
        with self.assertRaises(subprocess.CalledProcessError):
            support.run_grader(self.solved, self.out("run"), "NoSuchKoans")

    def test_infinite_loop_reported(self):
        line = "public static void sayHelloInConsole() {"

        def patch(java):
            path = java / "koans/english/AboutConsoleAndVariables.java"
            text = path.read_text()
            self.assertIn(line, text)
            path.write_text(text.replace(line, line + " if (true) { while (true) {} }"))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            classes = build("solved", root, patch)
            rows = support.run_grader(classes, root / "out.json", SERIES, timeout=300)
        self.assertEqual(len(rows), 8)
        looping, *others = rows
        self.assertEqual(looping["koan"], SAY_HELLO_KOAN)
        self.assertFalse(looping["passed"])
        self.assertNotEqual(looping["message"], "")
        for row in others:
            self.assertTrue(row["passed"], row)

    def test_lone_surrogate_in_output_is_escaped(self):
        # An exception message reaches the koan message as a Java String (console
        # output does not: it goes through UTF-8 bytes and becomes '?'). An
        # unpaired surrogate there would make writing the JSON throw, so the
        # Grader must escape it. A valid pair passes through.
        line = 'System.out.println("Hello!");'

        def patch(java):
            path = java / "koans/english/AboutConsoleAndVariables.java"
            text = path.read_text()
            self.assertIn(line, text)
            path.write_text(text.replace(
                line, 'if (true) throw new RuntimeException("a\\uD800b\\uD83D\\uDE00c");', 1))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            classes = build("solved", root, patch)
            out = root / "out.json"
            rows = support.run_grader(classes, out, SERIES)
            raw = out.read_text(encoding="utf-8")
        self.assertEqual(len(rows), 8)
        first = rows[0]
        self.assertEqual(first["koan"], SAY_HELLO_KOAN)
        self.assertFalse(first["passed"])
        self.assertIn("a\ud800b\U0001F600c", first["message"])
        self.assertIn("\\ud800", raw)
        self.assertIn("\U0001F600", raw)


if __name__ == "__main__":
    unittest.main()
