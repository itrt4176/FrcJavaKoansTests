"""Grade real checkouts through grade-local.sh against the built bundle."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import jsonschema

from classroom50.tests import support

BUNDLE = support.REPO / "build/classroom50/bundle"
GRADE_LOCAL = support.REPO / "classroom50/grade-local.sh"
SCHEMA = json.loads((support.REPO / "classroom50/result-v1.schema.json").read_text())
M = support.MILESTONES
TAGS = [m["tag"] for m in M]
REFS = TAGS + ["submit/verify"]
KINDS = ("solved", "blank", "broken")
WORKERS = max(1, min(4, os.cpu_count() or 1))


class Grading:
    def __init__(self, checkout: Path, proc: subprocess.CompletedProcess):
        self.checkout = checkout
        self.returncode = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        result = checkout / "result.json"
        body = checkout / "release-body.md"
        self.result = json.loads(result.read_text(encoding="utf-8")) if result.exists() else None
        self.body = body.read_text(encoding="utf-8") if body.exists() else None

    def describe(self):
        return f"exit {self.returncode}\nstdout:\n{self.stdout[-3000:]}\nstderr:\n{self.stderr[-3000:]}"


def grade(base: Path, dest: Path, ref: str, prepare=None) -> Grading:
    shutil.copytree(base, dest)
    if prepare:
        prepare(dest)
    env = {**os.environ, "JAVA_HOME": str(support.JAVA_HOME)}
    env.pop("CLASSROOM50_BUNDLE_DIR", None)
    proc = subprocess.run(["bash", str(GRADE_LOCAL), str(dest), ref],
                          capture_output=True, text=True, env=env)
    return Grading(dest, proc)


def add_cheat(checkout: Path):
    (checkout / "src/main/java/engine/Cheat.java").write_text("this is not java\n")


class EndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (BUNDLE / "autograder.py").exists():
            raise FileNotFoundError(
                f"no bundle at {BUNDLE}; run ./gradlew buildClassroomBundle")
        cls.manifest = json.loads((BUNDLE / "koans.json").read_text(encoding="utf-8"))
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        bases = {kind: support.make_checkout(kind, root / "base" / kind) for kind in KINDS}

        jobs = {}
        for kind in KINDS:
            for ref in REFS:
                dest = root / "runs" / f"{kind}-{ref.replace('/', '_')}"
                jobs[(kind, ref)] = (bases[kind], dest, ref, None)
        jobs[("cheat", "loops")] = (bases["blank"], root / "runs/cheat-loops", "loops", add_cheat)
        jobs[("blank", "nope")] = (bases["blank"], root / "runs/blank-nope", "nope", None)

        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {key: pool.submit(grade, *args) for key, args in jobs.items()}
            cls.gradings = {key: f.result() for key, f in futures.items()}

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def graded(self, kind, ref) -> Grading:
        g = self.gradings[(kind, ref)]
        self.assertEqual(g.returncode, 0, g.describe())
        self.assertIsNotNone(g.result, g.describe())
        self.assertIsNotNone(g.body, g.describe())
        stamped = {**g.result, "owner": "local", "assignment_type": "individual"}
        jsonschema.validate(stamped, SCHEMA, cls=jsonschema.Draft202012Validator)
        self.assertLessEqual(g.result["score"], g.result["max-score"])
        for t in g.result["tests"]:
            self.assertLessEqual(t["score"], t["max-score"], t)
        return g

    def listed_max(self, series_class):
        return sum(r["assertions"] for r in self.manifest if r["seriesClass"] == series_class)

    def test_solved_every_milestone(self):
        for m in M:
            with self.subTest(tag=m["tag"]):
                r = self.graded("solved", m["tag"]).result
                self.assertGreater(r["max-score"], 0)
                self.assertEqual(r["score"], r["max-score"])
                self.assertTrue(all(t["passed"] for t in r["tests"]))
                self.assertEqual(r["max-score"], self.listed_max(m["series"]))

    def test_solved_submit(self):
        r = self.graded("solved", "submit/verify").result
        self.assertGreater(r["max-score"], 0)
        self.assertEqual(r["score"], r["max-score"])
        self.assertTrue(all(t["passed"] for t in r["tests"]))

    def test_blank_scores_zero(self):
        for ref in REFS:
            with self.subTest(ref=ref):
                r = self.graded("blank", ref).result
                self.assertEqual(r["score"], 0)
                self.assertEqual(r["max-score"], self.gradings[("solved", ref)].result["max-score"])

    def test_broken_scores_zero(self):
        for ref in REFS:
            with self.subTest(ref=ref):
                g = self.graded("broken", ref)
                self.assertEqual(g.result["score"], 0)
                self.assertIn("Your code doesn't compile", g.body)
                self.assertEqual(g.result["max-score"],
                                 self.gradings[("solved", ref)].result["max-score"])

    def test_submit_full_course(self):
        g = self.graded("solved", "submit/verify")
        main_series = {r["series"] for r in self.manifest
                       if r["seriesClass"] in {m["series"] for m in M if not m["bonus"]}}
        self.assertEqual(len(main_series), 9)
        names = [t["test-name"] for t in g.result["tests"]]
        self.assertEqual({n.split(".", 1)[0] for n in names}, main_series)
        for n in names:
            self.assertFalse(n.startswith(("AboutArrays.", "AboutInterfaces.")), n)
        self.assertIn("# Full course:", g.body)
        self.assertIn("## Bonus", g.body)

    def test_overlay_discards_engine_edits(self):
        g = self.graded("cheat", "loops")
        self.assertNotIn("doesn't compile", g.body)
        self.assertFalse((g.checkout / "src/main/java/engine/Cheat.java").exists())

    def test_unknown_ref_errors(self):
        g = self.gradings[("blank", "nope")]
        self.assertNotEqual(g.returncode, 0)
        self.assertIsNone(g.result)


if __name__ == "__main__":
    unittest.main()
