"""Shared helpers for the Classroom 50 verification tests."""
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FORK = REPO.parent / "FrcJavaKoans"
JAVA_HOME = Path(os.environ.get("JAVA_HOME") or Path.home() / "wpilib/2026/jdk")
GRADER_SOURCE = REPO / "src/main/java/engine/Grader.java"
MILESTONES = json.loads((REPO / "classroom50/milestones.json").read_text())


def make_checkout(kind: str, dest: Path) -> Path:
    """Build a student checkout under dest: "blank", "solved", or "broken"."""
    if kind not in {"blank", "solved", "broken"}:
        raise ValueError(f"unknown checkout kind: {kind}")
    shutil.copytree(FORK / "src", dest / "src")
    java = dest / "src/main/java"
    if kind == "solved":
        shutil.copytree(REPO / "src/inject/passing", java, dirs_exist_ok=True)
    elif kind == "broken":
        with open(java / "koans/english/AboutConsoleAndVariables.java", "a") as f:
            f.write("this is not java\n")
    return dest


def compile_with_grader(src_main_java: Path, out: Path) -> None:
    sources = [str(p) for p in sorted(Path(src_main_java).rglob("*.java"))]
    sources.append(str(GRADER_SOURCE))
    result = subprocess.run(
        [str(JAVA_HOME / "bin/javac"), "-encoding", "UTF-8", "-d", str(out), *sources],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"javac failed ({result.returncode}):\n{result.stdout}{result.stderr}")


def run_grader(classes: Path, out_json: Path, *args: str, timeout=None) -> list[dict]:
    if "--list" in args:
        rest = [a for a in args if a != "--list"]
        argv = ["--list", str(out_json), *rest]
    else:
        argv = [str(out_json), *args]
    subprocess.run(
        [str(JAVA_HOME / "bin/java"), "-cp", str(classes), "engine.Grader", *argv],
        check=True, capture_output=True, timeout=timeout,
    )
    return json.loads(Path(out_json).read_text(encoding="utf-8"))
