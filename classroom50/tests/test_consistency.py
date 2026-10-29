import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MILESTONES = json.loads((HERE.parent / "milestones.json").read_text())
GHSUBMIT = ROOT.parent / "FrcJavaKoans/bin/ghsubmit"
WISDOM = ROOT.parent / "FrcJavaKoans/src/main/java/sensei/Wisdom.java"
SETUP = HERE.parent / "assignment-setup.sh"


def marker_tags(path):
    text = path.read_text()
    block = re.search(r"# milestones:begin\n(.*?)# milestones:end", text, re.S).group(1)
    body = re.search(r"=\(\n(.*?)\n\)", block, re.S).group(1)
    return body.split()


class ConsistencyTest(unittest.TestCase):
    def expected_tags(self):
        return [m["tag"] for m in MILESTONES]

    def test_ghsubmit_matches_milestones(self):
        self.assertEqual(marker_tags(GHSUBMIT), self.expected_tags())

    def test_setup_script_matches_milestones(self):
        self.assertEqual(marker_tags(SETUP), self.expected_tags())

    def test_series_match_wisdom(self):
        wisdom = re.findall(r"(\w+Koans)\.koans", WISDOM.read_text())
        series = [m["series"] for m in MILESTONES if not m["bonus"]]
        self.assertEqual(series, wisdom)


if __name__ == "__main__":
    unittest.main()
