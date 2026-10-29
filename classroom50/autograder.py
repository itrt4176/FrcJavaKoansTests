"""Classroom 50 autograder for FRC Java Koans (standard library only)."""
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, NamedTuple

MESSAGE_LIMIT = 2000
BODY_LIMIT = 100_000
COMPILE_LINES = 40
GRADER_TIMEOUT = 300

TRUNCATED_NOTE = "_Report truncated; see the grade log for the full output._"


class Scope(NamedTuple):
    label: str
    scored: list
    bonus: list


def load_milestones(path: Path) -> list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_scope(ref_name: str, milestones: list) -> Scope:
    if ref_name.startswith("submit/"):
        return Scope(
            "Full course",
            [m["series"] for m in milestones if not m["bonus"]],
            [m["series"] for m in milestones if m["bonus"]],
        )
    for m in milestones:
        if m["tag"] == ref_name:
            return Scope(ref_name, [m["series"]], [])
    raise ValueError(f"unknown ref: {ref_name!r}")


def failed_rows(manifest: list, series: list) -> list:
    wanted = set(series)
    return [
        {**r, "passed": False, "failedAssertions": r["assertions"], "message": ""}
        for r in manifest
        if r["seriesClass"] in wanted
    ]


def build_result(env: Mapping, rows: list) -> dict:
    tests = [
        {
            "test-name": f"{r['series']}.{r['koan']}",
            "passed": r["passed"],
            "score": r["assertions"] if r["passed"] else 0,
            "max-score": r["assertions"],
            "message": r["message"],
        }
        for r in rows
    ]
    return {
        "schema": "classroom50/result/v1",
        "classroom": env.get("CLASSROOM"),
        "assignment": env.get("ASSIGNMENT"),
        "submission": env.get("SUBMISSION"),
        "commit": env.get("COMMIT"),
        "release": env.get("RELEASE"),
        "review": env.get("REVIEW_URL") or env.get("COMMIT_URL"),
        "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "score": sum(t["score"] for t in tests),
        "max-score": sum(t["max-score"] for t in tests),
        "tests": tests,
    }


def _fence(text: str) -> tuple:
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(4, longest + 1)


def _fenced(text: str) -> str:
    f = _fence(text)
    return f"{f}text\n{text}\n{f}"


def _cell(text: str) -> str:
    return html.escape(text).replace("|", "\\|").replace("\n", " ")


def _failure_block(r: dict) -> str:
    message = r["message"]
    if len(message) > MESSAGE_LIMIT:
        message = message[:MESSAGE_LIMIT] + "\n... (truncated)"
    summary = html.escape(
        f"{r['series']}.{r['koan']}: {r['failedAssertions']} of {r['assertions']} assertions failed"
    )
    return f"<details><summary>{summary}</summary>\n\n{_fenced(message)}\n\n</details>\n"


def render_body(scope: Scope, rows: list, bonus_rows: list, compile_output) -> str:
    score = sum(r["assertions"] for r in rows if r["passed"])
    total = sum(r["assertions"] for r in rows)
    head = [f"# {scope.label}: {score}/{total}\n"]
    if compile_output is not None:
        lines = compile_output.splitlines()[:COMPILE_LINES]
        head.append("## Your code doesn't compile\n\n" + _fenced("\n".join(lines)) + "\n")
    table = ["## Koans\n", "| Koan | Points | Result |", "| --- | --- | --- |"]
    for r in rows:
        earned = r["assertions"] if r["passed"] else 0
        table.append(
            f"| {_cell(r['series'] + '.' + r['koan'])} | {earned}/{r['assertions']} "
            f"| {'✅' if r['passed'] else '❌'} |"
        )
    head.append("\n".join(table) + "\n")
    head_text = "\n".join(head)

    tail_text = ""
    if bonus_rows:
        bonus = ["## Bonus\n", "| Koan | Result |", "| --- | --- |"]
        for r in bonus_rows:
            bonus.append(f"| {_cell(r['series'] + '.' + r['koan'])} | {'✅' if r['passed'] else '❌'} |")
        tail_text = "\n" + "\n".join(bonus) + "\n"

    failing = [r for r in rows if not r["passed"]]
    failures_text = ""
    truncated = False
    if failing:
        heading = "\n## What failed\n\n"
        reserve = len(head_text) + len(tail_text) + len(heading) + len(TRUNCATED_NOTE) + 2
        used = reserve
        blocks = []
        for r in failing:
            block = _failure_block(r)
            if used + len(block) + 1 > BODY_LIMIT:
                truncated = True
                break
            blocks.append(block)
            used += len(block) + 1
        failures_text = heading + "\n".join(blocks)
    body = head_text + failures_text + tail_text
    if truncated:
        body += "\n" + TRUNCATED_NOTE
    return body
