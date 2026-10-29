import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[3] / "FrcJavaKoans/bin/ghsubmit"


def git(*args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check,
                          capture_output=True, text=True)


def configure(repo):
    git("config", "user.name", "Test", cwd=repo)
    git("config", "user.email", "test@example.com", cwd=repo)


class GhsubmitTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.remote = root / "remote.git"
        self.work = root / "work"
        git("init", "--bare", "-b", "main", str(self.remote), cwd=root)
        git("clone", str(self.remote), str(self.work), cwd=root)
        configure(self.work)
        git("checkout", "-B", "main", cwd=self.work)
        (self.work / "file.txt").write_text("one\n")
        (self.work / "bin").mkdir()
        shutil.copy(SCRIPT, self.work / "bin" / "ghsubmit")
        git("add", ".", cwd=self.work)
        git("commit", "-m", "init", cwd=self.work)
        git("push", "-u", "origin", "main", cwd=self.work)

    def run_script(self, *args, stdin="", cwd=None):
        return subprocess.run(["bash", "bin/ghsubmit", *args], input=stdin,
                              cwd=cwd or self.work, capture_output=True, text=True)

    def remote_tag(self, name):
        out = git("ls-remote", str(self.remote), f"refs/tags/{name}", cwd=self.work).stdout
        return out.split()[0] if out.strip() else None

    def head(self):
        return git("rev-parse", "HEAD", cwd=self.work).stdout.strip()

    def commit_change(self, text):
        (self.work / "file.txt").write_text(text)
        git("commit", "-am", "change", cwd=self.work)

    def test_argument_tags_and_pushes(self):
        r = self.run_script("loops")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.remote_tag("loops"), self.head())

    def test_resubmit_moves_tag(self):
        self.assertEqual(self.run_script("loops").returncode, 0)
        self.commit_change("two\n")
        r = self.run_script("loops")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.remote_tag("loops"), self.head())

    def test_menu_selection(self):
        r = self.run_script(stdin="6\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.remote_tag("loops"), self.head())

    def test_unknown_milestone(self):
        r = self.run_script("nope")
        self.assertEqual(r.returncode, 2)
        self.assertIsNone(self.remote_tag("nope"))
        self.assertEqual(git("ls-remote", "--tags", str(self.remote), cwd=self.work).stdout, "")

    def test_dirty_tree_abort(self):
        (self.work / "file.txt").write_text("dirty\n")
        r = self.run_script("loops", stdin="n\n")
        self.assertEqual(r.returncode, 1)
        self.assertIsNone(self.remote_tag("loops"))

    def test_runs_from_subdirectory(self):
        r = subprocess.run(["bash", "ghsubmit", "methods"], cwd=self.work / "bin",
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.remote_tag("methods"), self.head())

    def test_stops_when_push_rejected(self):
        other = Path(self._tmp.name) / "other"
        git("clone", str(self.remote), str(other), cwd=self._tmp.name)
        configure(other)
        (other / "x.txt").write_text("x\n")
        git("add", ".", cwd=other)
        git("commit", "-m", "other", cwd=other)
        git("push", "origin", "HEAD:main", cwd=other)
        r = self.run_script("loops")
        self.assertEqual(r.returncode, 1)
        self.assertIsNone(self.remote_tag("loops"))


if __name__ == "__main__":
    unittest.main()
