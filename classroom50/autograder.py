"""Classroom 50 autograder for FRC Java Koans (standard library only).

Runs standalone as `python3 -I <bundle>/autograder.py` with the student's
checkout as the working directory; the bundle folder holds milestones.json,
koans.json, and pristine src/engine and src/sensei trees.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, NamedTuple

MESSAGE_LIMIT = 2000
BODY_LIMIT = 100_000
COMPILE_LINES = 40
COMPILE_CHARS = 10_000
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


def _fence(text: str) -> str:
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
        text = "\n".join(compile_output.splitlines()[:COMPILE_LINES])
        if len(text) > COMPILE_CHARS:
            text = text[:COMPILE_CHARS] + "\n... (truncated)"
        head.append("## Your code doesn't compile\n\n" + _fenced(text) + "\n")
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

    # A compile failure fails every koan with no message; the compiler output
    # above already explains it, so leave out the per-koan section.
    failing = [] if compile_output is not None else [
        r for r in rows if not r["passed"] and r["message"]
    ]
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


# ---------------------------------------------------------------------------
# Runtime: overlay, compile, grade, report.

OVERLAID = ("engine", "sensei")
LOG_TAIL = 4000


class GraderError(RuntimeError):
    """The Grader crashed, timed out, or produced no usable output."""


def bundle_dir() -> Path:
    env = os.environ.get("CLASSROOM50_BUNDLE_DIR")
    return Path(env) if env else Path(__file__).resolve().parent


def java_tool(name: str) -> str:
    home = os.environ.get("JAVA_HOME")
    return str(Path(home) / "bin" / name) if home else name


def overlay(bundle_src: Path, checkout_src: Path) -> None:
    for name in OVERLAID:
        target = Path(checkout_src) / name
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        shutil.copytree(Path(bundle_src) / name, target)


def compile_sources(src: Path, out: Path) -> tuple[bool, str]:
    sources = sorted(str(p) for p in Path(src).rglob("*.java"))
    Path(out).mkdir(parents=True, exist_ok=True)
    argfile = Path(out).parent / "javac-sources.txt"
    argfile.write_text("\n".join(f'"{s}"' for s in sources) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [java_tool("javac"), "-encoding", "UTF-8", "-d", str(out), f"@{argfile}"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace",
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def _tail(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-LOG_TAIL:]


def run_grader(classes: Path, series: list[str], timeout: int = GRADER_TIMEOUT) -> list[dict]:
    work = Path(tempfile.mkdtemp(prefix="grader-"))
    try:
        out_json = work / "rows.json"
        log = work / "grader.log"
        argv = [java_tool("java"), "-cp", str(classes), "engine.Grader", str(out_json), *series]
        with open(log, "wb") as log_file:
            try:
                proc = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=log_file,
                                      stderr=subprocess.STDOUT, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise GraderError(f"Grader timed out after {timeout} seconds and was killed\n"
                                  + _tail(log)) from None
        if proc.returncode != 0:
            raise GraderError(f"Grader exited with status {proc.returncode}\n" + _tail(log))
        if not out_json.exists():
            raise GraderError("Grader exited 0 but wrote no output file\n" + _tail(log))
        text = out_json.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            raise GraderError("Grader wrote an empty output file\n" + _tail(log))
        try:
            rows = json.loads(text)
        except json.JSONDecodeError as e:
            raise GraderError(f"Grader wrote invalid JSON: {e}\n" + _tail(log)) from None
        if not isinstance(rows, list):
            raise GraderError("Grader output is not a JSON array")
        missing = set(series) - {r.get("seriesClass") for r in rows}
        if missing:
            raise GraderError(f"Grader output has no rows for {sorted(missing)}")
        return rows
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _ref_name(environ: Mapping) -> str:
    name = environ.get("GITHUB_REF_NAME")
    if name:
        return name
    ref = environ.get("GITHUB_REF", "")
    return ref[len("refs/tags/"):] if ref.startswith("refs/tags/") else ref


def _result_env(environ: Mapping) -> dict:
    """Map the Classroom 50 runner's variables onto build_result's keys."""
    return {
        "CLASSROOM": environ.get("CLASSROOM"),
        "ASSIGNMENT": environ.get("ASSIGNMENT"),
        "SUBMISSION": environ.get("SUBMISSION_TAG"),
        "COMMIT": environ.get("COMMIT_URL"),
        "RELEASE": environ.get("RELEASE_URL"),
        "REVIEW_URL": environ.get("REVIEW_URL"),
        "COMMIT_URL": environ.get("COMMIT_URL"),
    }


def _error(message: str) -> int:
    print(f"autograder: {message}", file=sys.stderr)
    return 1


def main() -> int:
    # Student output can hold lone surrogates; never let logging or writing it crash grading.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    bundle = bundle_dir()
    milestones = load_milestones(bundle / "milestones.json")
    ref = _ref_name(os.environ)
    try:
        scope = resolve_scope(ref, milestones)
    except ValueError as e:
        return _error(str(e))
    manifest = json.loads((bundle / "koans.json").read_text(encoding="utf-8"))
    series = scope.scored + scope.bonus

    checkout_src = Path("src/main/java")
    overlay(bundle / "src", checkout_src)

    compile_output = None
    with tempfile.TemporaryDirectory(prefix="koans-") as tmp:
        classes = Path(tmp) / "classes"
        ok, output = compile_sources(checkout_src, classes)
        if ok:
            try:
                rows_all = run_grader(classes, series, timeout=GRADER_TIMEOUT)
            except GraderError as e:
                return _error(str(e))
        else:
            compile_output = output
            print("Your code doesn't compile:\n" + output)
            rows_all = failed_rows(manifest, series)

    scored = set(scope.scored)
    rows = [r for r in rows_all if r["seriesClass"] in scored]
    bonus_rows = [r for r in rows_all if r["seriesClass"] not in scored]

    for r in rows_all:
        if not r["passed"] and r["message"]:
            tag = " (bonus)" if r["seriesClass"] not in scored else ""
            print(f"=== {r['series']}.{r['koan']}{tag}: "
                  f"{r['failedAssertions']} of {r['assertions']} assertions failed ===")
            print(r["message"])

    result = build_result(_result_env(os.environ), rows)
    Path("result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    body = render_body(scope, rows, bonus_rows, compile_output)
    Path("release-body.md").write_text(body, encoding="utf-8", errors="backslashreplace")
    print(f"{scope.label}: {result['score']}/{result['max-score']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
