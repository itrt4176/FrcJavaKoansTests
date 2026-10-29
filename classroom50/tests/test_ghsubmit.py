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

    def remote_main(self):
        out = git("ls-remote", str(self.remote), "refs/heads/main", cwd=self.work).stdout
        return out.split()[0]

    def tree(self, rev):
        return git("rev-parse", f"{rev}^{{tree}}", cwd=self.work).stdout.strip()

    def assert_submitted(self, tag, before):
        """The tag sits on a new "Submit <tag>" commit on top of `before`,
        which is also the local HEAD and the remote branch tip."""
        sha = self.remote_tag(tag)
        self.assertIsNotNone(sha)
        self.assertNotEqual(sha, before)
        self.assertEqual(sha, self.head())
        self.assertEqual(sha, self.remote_main())
        parent = git("rev-parse", f"{sha}^", cwd=self.work).stdout.strip()
        self.assertEqual(parent, before)
        self.assertEqual(self.tree(sha), self.tree(before))
        subject = git("log", "-1", "--format=%s", sha, cwd=self.work).stdout.strip()
        self.assertEqual(subject, f"Submit {tag}")
        return sha

    def commit_change(self, text):
        (self.work / "file.txt").write_text(text)
        git("commit", "-am", "change", cwd=self.work)

    def test_argument_tags_and_pushes(self):
        before = self.head()
        r = self.run_script("loops")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assert_submitted("loops", before)

    def test_resubmit_moves_tag(self):
        self.assertEqual(self.run_script("loops").returncode, 0)
        self.commit_change("two\n")
        before = self.head()
        r = self.run_script("loops")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assert_submitted("loops", before)

    def test_resubmit_without_new_work_moves_tag(self):
        self.assertEqual(self.run_script("loops").returncode, 0)
        first = self.remote_tag("loops")
        r = self.run_script("loops")
        self.assertEqual(r.returncode, 0, r.stderr)
        second = self.assert_submitted("loops", first)
        self.assertNotEqual(second, first)

    def test_two_milestones_from_one_commit_get_different_shas(self):
        self.assertEqual(self.run_script("methods").returncode, 0)
        r = self.run_script("conditions")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(self.remote_tag("methods"), self.remote_tag("conditions"))

    def test_menu_selection(self):
        before = self.head()
        r = self.run_script(stdin="6\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assert_submitted("loops", before)

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

    def test_dirty_tree_continue_leaves_changes_out(self):
        before = self.head()
        (self.work / "file.txt").write_text("dirty\n")
        (self.work / "staged.txt").write_text("staged\n")
        git("add", "staged.txt", cwd=self.work)
        r = self.run_script("loops", stdin="y\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assert_submitted("loops", before)
        # The uncommitted and staged changes are still there, uncommitted.
        self.assertEqual((self.work / "file.txt").read_text(), "dirty\n")
        status = git("status", "--porcelain", cwd=self.work).stdout
        self.assertIn(" M file.txt", status)
        self.assertIn("A  staged.txt", status)

    def test_detached_head(self):
        git("checkout", "--detach", cwd=self.work)
        r = self.run_script("loops")
        self.assertEqual(r.returncode, 1)
        self.assertIn("You are not on a branch; switch to your main branch first.", r.stderr)
        self.assertIsNone(self.remote_tag("loops"))

    def test_runs_from_subdirectory(self):
        before = self.head()
        r = subprocess.run(["bash", "ghsubmit", "methods"], cwd=self.work / "bin",
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assert_submitted("methods", before)

    def test_stops_when_push_rejected(self):
        other = Path(self._tmp.name) / "other"
        git("clone", str(self.remote), str(other), cwd=self._tmp.name)
        configure(other)
        (other / "x.txt").write_text("x\n")
        git("add", ".", cwd=other)
        git("commit", "-m", "other", cwd=other)
        git("push", "origin", "HEAD:main", cwd=other)
        before = self.head()
        r = self.run_script("loops")
        self.assertEqual(r.returncode, 1)
        self.assertIsNone(self.remote_tag("loops"))
        # The submit commit made by this run is undone.
        self.assertEqual(self.head(), before)


if __name__ == "__main__":
    unittest.main()
