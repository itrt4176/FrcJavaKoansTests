# FRC Java Koans on Classroom 50 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `itrt4176/FrcJavaKoans` into an English-only Classroom 50 template with a `ghsubmit` command, and build the grading bundle and its verification in `itrt4176/FrcJavaKoansTests`.

**Architecture:** Students push one of 11 milestone tags; Classroom 50 runs our `autograder.py` from a bundle. The autograder overlays pristine `engine/` and `sensei/`, compiles, runs `engine.Grader` (a `TestSensei` wrapper) on the milestone's series, and writes `result.json` and `release-body.md`. Everything grading-related lives in the tests repo; the fork gets only student-facing changes.

**Tech Stack:** Java 17 (no build tool in the fork; Gradle wrapper in the tests repo), Python 3 standard library (autograder), `unittest` + `jsonschema` in a venv (verification only), bash (`ghsubmit`, scripts).

**Spec:** `docs/superpowers/specs/2026-10-29-classroom50-koans-design.md` (this repo). Read it before starting any task.

## Global Constraints

- Repo paths: the fork is `../FrcJavaKoans` relative to this repo (default branch `master`); this repo's default branch is `main`. Both are checked out side by side under `KoansClass/`.
- Java: JDK 17. Locally use `~/wpilib/2026/jdk` (`JAVA_HOME=~/wpilib/2026/jdk`), never the system JDK 21. Classroom 50 runtime: `{ "java": "17" }`.
- The fork stays free of build tools, dependencies, grading code, and solutions.
- `autograder.py` uses the Python standard library only. `jsonschema` is allowed only in the verification venv.
- Milestones, in this order (tag → `sensei` class, bonus flag): `console-and-variables` → `AboutConsoleAndVariablesKoans`, `methods` → `AboutMethodsKoans`, `conditions` → `AboutConditionsKoans`, `more-methods` → `AboutMoreMethodsKoans`, `decimal-numbers` → `AboutDecimalNumbersKoans`, `loops` → `AboutLoopsKoans`, `not7-game` → `AboutNot7GameKoans`, `classes` → `AboutClassesKoans`, `objects` → `AboutObjectsKoans`, `arrays` → `AboutArraysKoans` (bonus), `interfaces` → `AboutInterfacesKoans` (bonus).
- Report limits: each failure message cut at 2,000 characters; release body capped at 100,000 characters; first 40 lines of `javac` output; Grader timeout 300 seconds.
- Release copy strings fixed by the spec: heading label "Full course" for `submit/*`; compile-failure heading "Your code doesn't compile"; per-koan summary "N of M assertions failed".
- Commits: Conventional Commits, committed directly to the default branch, no attribution lines. Do not push; Nick pushes.
- Never edit, build, or run anything inside `../classroom50/`; reading it is fine.

## Review Focus

1. A student's Sensei output so long that the report exceeds the body cap. Expected: the body stays under 100,000 characters and ends with the truncation note. Test: `test_body_capped` in Task 6.
2. A failure message that contains a triple-backtick fence or HTML. Expected: it stays inside its code block and doesn't break later sections. Test: `test_message_fence_safe` in Task 6.
3. Student code with an infinite loop. Expected: the Grader still finishes and reports the koan as failed with a message. Test: `test_infinite_loop_reported` in Task 5.
4. `ghsubmit` run from a subdirectory of the workspace. Expected: it finds the repo root and submits normally. Test: `test_runs_from_subdirectory` in Task 3.
5. `ghsubmit` when the branch push is rejected (remote is ahead). Expected: it stops before tagging, and no milestone tag reaches the remote. Test: `test_stops_when_push_rejected` in Task 3.

---

### Task 1: Remove French from the fork

**Files (in `../FrcJavaKoans`):**
- Delete: `src/main/java/koans/french/`, `src/main/java/bonuses/french/`, `src/main/java/FrenchPathToEnlightment.java`, `AideMémoireJava.pdf`, `release.ps1`
- Modify: `src/main/java/engine/text/Locale.java`, `src/main/java/engine/text/Localizable.java`, `src/main/java/engine/Texts.java`, `src/main/java/sensei/Texts.java`, `src/main/java/sensei/About*Koans.java` (11 files), `src/main/java/engine/test/{EqualityAssertionsTests,ExpressionTests,FmtTests}.java`
- Check: `.vscode/` and `CONTRIBUTING.md` for references to removed files

**Interfaces:**
- Produces: `engine.text.Locale` with the single value `en`; `Localizable<T>` without the `fr(T)` method. Later tasks call `Locale.en`.

- [ ] **Step 1: Record the baseline.** Run from the fork root:
  `J=~/wpilib/2026/jdk/bin; rm -rf /tmp/koans-out; $J/javac -d /tmp/koans-out $(find src/main/java -name '*.java') && $J/java -cp /tmp/koans-out engine.test.runner.TestRunner`
  Expected: ends with `185/185`.
- [ ] **Step 2: Delete the French files and `release.ps1`** listed above.
- [ ] **Step 3: Remove every `.fr(...)` call.** In each file listed above, delete each `.fr(<argument>)` call that follows a `local(...)`/`localClass(...)` expression, including the newline before it. Arguments can span lines and contain parentheses, so match balanced parentheses (a one-off script in the session scratchpad is fine; do not commit it). Then remove `fr` from `Locale`, and remove `fr(T)` from `Localizable` and `Local`. Update the Javadoc of `Local` if it mentions French.
- [ ] **Step 4: Fix references** in `.vscode/` (launch configs) and `CONTRIBUTING.md` that point at deleted files. If `CONTRIBUTING.md` documents adding a locale, keep that section but drop French examples that no longer exist.
- [ ] **Step 5: Run the engine tests.** Same command as Step 1, plus `grep -rn "french\|\.fr(\|Locale\.fr" src/main/java` (expect no output).
  Expected: every test passes. Note the new `N/N`; it is needed in Task 2.
- [ ] **Step 6: Commit (fork).**
  ```bash
  git -C ../FrcJavaKoans add -A
  git -C ../FrcJavaKoans commit -m "feat!: drop the French locale" -m "The team's course is English only. Removes the French koans, bonuses, path file, cheat sheet, and the fr Locale value, and the zip release script that Classroom 50 accept replaces."
  ```

### Task 2: English-only solutions in this repo

**Files:**
- Delete: `src/inject/passing/koans/french/`, `src/inject/passing/bonuses/french/`
- Modify: `src/main/java/org/frc/Main.java` (`main`: run `executeSuiteListsIn(Locale.en)` once instead of looping over `Locale.values()`, and drop the `System.setProperty("locale", ...)` call only if nothing reads it: `grep -rn '"locale"' ../FrcJavaKoans/src` returns nothing today)
- Modify (workspace, not in git): `../CLAUDE.md`, the two expected counts

**Interfaces:**
- Consumes: Task 1's `Locale.en`.

- [ ] **Step 1: Run `JAVA_HOME=~/wpilib/2026/jdk ./gradlew run`** with Task 1 in place. Expected: it passes, with about half the old assertion count, because `Locale.values()` is now only `en` and the French solution files still compile but nothing runs them. If it fails, the error must come from a French solution file; Step 2 removes them.
- [ ] **Step 2: Delete the French solutions and simplify `Main.main`** as listed.
- [ ] **Step 3: Run `JAVA_HOME=~/wpilib/2026/jdk ./gradlew run`.** Expected: ends with `N/N assertions executed successfully in M koans.`, where N is about half of 512 and M is 81 (64 main + 17 bonus).
- [ ] **Step 4: Update `../CLAUDE.md`.** Replace `185/185` with Task 1's new count, and `512/512 in 162` with this task's numbers. Don't commit it; that file isn't in git.
- [ ] **Step 5: Commit.**
  ```bash
  git add -A src
  git commit -m "test: drop French solutions and run English only"
  ```

### Task 3: `ghsubmit` command and devcontainer PATH

**Files:**
- Create: `../FrcJavaKoans/bin/ghsubmit` (mode 100755)
- Modify: `../FrcJavaKoans/.devcontainer/devcontainer.json` (add top-level `"remoteEnv": { "PATH": "${containerEnv:PATH}:${containerWorkspaceFolder}/bin" }`)
- Test: `classroom50/tests/test_ghsubmit.py` (this repo)
- Create: `classroom50/__init__.py` and `classroom50/tests/__init__.py` (both empty, so `unittest discover -s classroom50 -t .` imports them as packages and tests can `from classroom50 import autograder`)

**Interfaces:**
- Produces: `ghsubmit [milestone]`. With no argument, it shows a numbered menu (1 = `console-and-variables` … 11 = `interfaces`) and reads a number from stdin. With an argument, it skips the menu. Exit 0 on success, 1 on user abort or git failure, 2 on an unknown milestone. The milestone list sits between the lines `# milestones:begin` and `# milestones:end`, as a bash array `MILESTONES=(` with one tag per line and a closing `)`. Task 8 parses this block.

- [ ] **Step 1: Write the failing tests** in `classroom50/tests/test_ghsubmit.py` (`unittest`). The fixture creates, under a `tempfile.TemporaryDirectory`, a bare repo `remote.git` and a clone `work` with one commit. The fixture copies `../FrcJavaKoans/bin/ghsubmit` (resolved from this file's location: `Path(__file__).parents[3] / "FrcJavaKoans/bin/ghsubmit"`) into `work/bin/`. It sets `user.name`/`user.email` locally and runs the script with `subprocess.run(["bash", "bin/ghsubmit", ...], input=..., cwd=work)`. Tests:
  - `test_argument_tags_and_pushes`: `ghsubmit loops` → exit 0; `git ls-remote remote.git refs/tags/loops` SHA == `git rev-parse HEAD` in `work`.
  - `test_resubmit_moves_tag`: submit `loops`, add a commit, submit `loops` again → exit 0; the remote tag equals the new HEAD.
  - `test_menu_selection`: no argument, stdin `"6\n"` → remote has `refs/tags/loops`.
  - `test_unknown_milestone`: `ghsubmit nope` → exit 2; remote has no tags.
  - `test_dirty_tree_abort`: modify a tracked file, stdin `"n\n"` with argument `loops` → exit 1; remote has no tags.
  - `test_runs_from_subdirectory`: run with `cwd=work/bin` and argument `methods` (as `bash ghsubmit methods`) → exit 0; remote has `refs/tags/methods`.
  - `test_stops_when_push_rejected`: a second clone pushes a new commit to `remote.git`; then `ghsubmit loops` in `work` → exit 1; remote has no `refs/tags/loops`.
- [ ] **Step 2: Run `python3 -m unittest discover -s classroom50 -t .` from this repo's root.** Expected: all 7 fail (script missing).
- [ ] **Step 3: Write `bin/ghsubmit`** (bash, `set -euo pipefail`). Steps:
  1. Find the repo root with `git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel` and `cd` there.
  2. Pick the milestone from the argument or the menu. Exit 2 on an unknown name or number.
  3. If `git status --porcelain` is non-empty, warn that uncommitted changes won't be submitted and ask `Submit anyway? [y/N]`. Anything but `y`/`Y` exits 1.
  4. `git push origin HEAD`, exiting 1 on failure with a message to pull first.
  5. `git tag -f "$m"`, then `git push -f origin "refs/tags/$m"`.
  6. Print `Submitted <m>. Your results will appear at https://github.com/<owner>/<repo>/releases in a few minutes.` Derive owner/repo from `git remote get-url origin` for `git@github.com:` and `https://github.com/` forms; for any other remote, print the line without a URL.
- [ ] **Step 4: Add `remoteEnv`** to `devcontainer.json` as listed (valid JSON; keep existing keys).
- [ ] **Step 5: Run the tests again.** Expected: 7 passed.
- [ ] **Step 6: Commit both repos.**
  ```bash
  git -C ../FrcJavaKoans add bin/ghsubmit .devcontainer/devcontainer.json
  git -C ../FrcJavaKoans commit -m "feat: add ghsubmit command for milestone submissions"
  git add classroom50/tests
  git commit -m "test: cover ghsubmit milestone submission"
  ```
  Before committing, check the mode with `git -C ../FrcJavaKoans ls-files -s bin/ghsubmit` (expect `100755`).

### Task 4: README rewrite (fork)

**Files:**
- Replace: `../FrcJavaKoans/README.md`
- Keep: `../FrcJavaKoans/images/` files the new README still uses. Delete images no longer referenced by any file (`grep -rn "images/" ../FrcJavaKoans` to check).

**Interfaces:**
- Consumes: `ghsubmit` from Task 3 and the milestone names from Global Constraints.

- [ ] **Step 1: Read the current README's credits and license sections** and note the license name and the original author's credits. They must carry over unchanged in substance.
- [ ] **Step 2: Write the new README** as assignment instructions, English only, in this order:
  - what the koans are (2–3 sentences)
  - **Getting started:** accept the assignment from the link your coach gives you; open your repo in Tiger Code at `https://itrt.dev/itrt4176/<your repo name>`
  - **Running the koans:** right-click `src/main/java/EnglishPathToEnlightment.java` → Run Java; how to read the Sensei's output, reusing the existing explanation and screenshots that still apply
  - **Submitting:** commit your work, run `ghsubmit` in the terminal, pick the series; resubmitting is fine
  - a table of the 11 milestones and which file each covers (bonuses marked as bonus)
  - **Your results:** the repo's Releases page, one Release per submission, listing what passed and what failed
  - **Credits and license:** jletroui's FrcJavaKoans as the original, with a link to `https://github.com/jletroui/FrcJavaKoans`, and the license from Step 1
  
  Drop the Codespaces, zip download, and French sections.
- [ ] **Step 3: Verify.** `grep -n "Codespaces\|release\.ps1\|zip\|Français\|french" ../FrcJavaKoans/README.md` returns nothing, and every `images/...` path in the README exists.
- [ ] **Step 4: Commit (fork).**
  ```bash
  git -C ../FrcJavaKoans add -A README.md images
  git -C ../FrcJavaKoans commit -m "docs: rewrite README as Classroom 50 assignment instructions"
  ```

### Task 5: Milestone list and `engine.Grader`

**Files:**
- Create: `classroom50/milestones.json`
- Create: `src/main/java/engine/Grader.java`
- Create: `classroom50/tests/support.py`, `classroom50/tests/test_grader.py`
- Create: `classroom50/verify.sh`
- Modify: `build.gradle` (add task `verifyClassroom`)

**Interfaces:**
- Produces:
  - `classroom50/milestones.json`: a JSON array, in Global Constraints order, of `{"tag": str, "series": str, "bonus": bool}`.
  - `java -cp <classes> engine.Grader <out.json> <SeriesClass>...` writes a JSON array with one row per koan, in argument order then koan order: `{"seriesClass": "AboutLoopsKoans", "series": "AboutLoops", "koan": "<koanName>", "assertions": int, "failedAssertions": int, "passed": bool, "message": str}`. `message` is the captured output of the first failing test with ANSI escapes (`\u001b\[[0-9;]*m`) removed, or `""`. The file is UTF-8 JSON. Exit 0 when done; an unknown series class throws, exiting nonzero.
  - `java -cp <classes> engine.Grader --list <out.json> <SeriesClass>...` writes the same rows with only `seriesClass`, `series`, `koan`, and `assertions`, without executing anything.
  - `support.py`: `JAVA_HOME: Path` (env `JAVA_HOME`, else `~/wpilib/2026/jdk`); `FORK: Path` (`../FrcJavaKoans` from the repo root); `REPO: Path`; `make_checkout(kind: str, dest: Path) -> Path` with `kind` in `{"blank", "solved", "broken"}`. `blank` copies `FORK/src`; `solved` additionally copies `REPO/src/inject/passing/**` over `dest/src/main/java`; `broken` is `blank` with the line `this is not java` appended to `src/main/java/koans/english/AboutConsoleAndVariables.java`. Plus `compile_with_grader(src_main_java: Path, out: Path) -> None`, which runs `javac` on every `.java` under the directory plus `REPO/src/main/java/engine/Grader.java` and raises on failure; and `run_grader(classes: Path, out_json: Path, *args: str) -> list[dict]`.
  - `classroom50/verify.sh`: runs `python3 -m unittest discover -s classroom50 -t .` from the repo root (Task 7 changes it to use the venv). Gradle `verifyClassroom` is an `Exec` task running `bash classroom50/verify.sh`, `dependsOn syncKoansEngine`.

- [ ] **Step 1: Write `milestones.json`** with the 11 entries from Global Constraints.
- [ ] **Step 2: Write the failing tests** in `test_grader.py`:
  - `test_solved_series_all_pass`: solved checkout, `run_grader(..., "AboutConsoleAndVariablesKoans")` → 8 rows; every `passed` is true, `failedAssertions` 0, `assertions` > 0, `message == ""`; every `series == "AboutConsoleAndVariables"`.
  - `test_blank_series_all_fail_with_message`: blank checkout, same series → every `passed` false, `failedAssertions == assertions`, `message` non-empty, and `"\x1b"` not in any message.
  - `test_list_mode_matches_run`: on the solved checkout, `--list` for all 11 series in `milestones.json` gives the same `(seriesClass, koan, assertions)` sequence as a full run, with 81 rows in total.
  - `test_unknown_series_fails`: `run_grader` with `NoSuchKoans` raises `CalledProcessError`.
  - `test_infinite_loop_reported`: solved checkout, then in `koans/english/AboutConsoleAndVariables.java` replace `public static void sayHelloInConsole() {` with that line followed by `if (true) { while (true) {} }`. Run the series with a 300-second subprocess timeout. The row for koan `sayHelloInConsole` has `passed` false and a non-empty message; the others pass.
- [ ] **Step 3: Run `bash classroom50/verify.sh`.** Expected: the Grader tests fail (class missing); the Task 3 tests still pass.
- [ ] **Step 4: Implement `engine.Grader`** (package `engine`, to read `Koan`'s package-private `koanClass`, `koanName`, `tests`). Load each series with `Class.forName("sensei." + name).getField("koans")`. Use `TestSensei.execute(koan, Locale.en)`, and take the message from `outputCapture().capturedStdOutAsString()`. Write JSON by hand (escape `"`, `\`, and control characters as `\uXXXX`), so the class has no dependencies.
- [ ] **Step 5: Add the Gradle `verifyClassroom` task** as specified in Interfaces.
- [ ] **Step 6: Run `JAVA_HOME=~/wpilib/2026/jdk ./gradlew verifyClassroom`.** Expected: all tests pass, and `./gradlew run` still passes.
- [ ] **Step 7: Commit.**
  ```bash
  git add classroom50 src/main/java/engine/Grader.java build.gradle
  git commit -m "feat: add koan Grader and milestone list"
  ```

### Task 6: Autograder scope, result, and report

**Files:**
- Create: `classroom50/autograder.py` (pure functions only in this task)
- Test: `classroom50/tests/test_autograder.py`

**Interfaces:**
- Consumes: Grader row format and `milestones.json` (Task 5).
- Produces (in `autograder.py`):
  - Constants: `MESSAGE_LIMIT = 2000`, `BODY_LIMIT = 100_000`, `COMPILE_LINES = 40`, `GRADER_TIMEOUT = 300`.
  - `class Scope(NamedTuple): label: str; scored: list[str]; bonus: list[str]` (lists of `sensei` class names).
  - `load_milestones(path: Path) -> list[dict]`.
  - `resolve_scope(ref_name: str, milestones: list[dict]) -> Scope`. A milestone tag gives `Scope(tag, [series], [])`. A name starting with `submit/` gives `Scope("Full course", <9 non-bonus series in order>, <2 bonus series>)`. Anything else raises `ValueError`.
  - `failed_rows(manifest: list[dict], series: list[str]) -> list[dict]`: manifest rows (from `--list`) for those series, as full Grader rows with `passed=False`, `failedAssertions=assertions`, `message=""`.
  - `build_result(env: Mapping[str, str], rows: list[dict]) -> dict`: `classroom50/result/v1`. Includes `classroom`, `assignment`, `submission`, `commit`, `release`, and `review` (`REVIEW_URL` or `COMMIT_URL`) from env, plus `datetime` (now, UTC, `%Y-%m-%dT%H:%M:%SZ`) and `tests`. Each test is `{"test-name": f"{series}.{koan}", "passed", "score": assertions if passed else 0, "max-score": assertions, "message"}`. Includes the `score`/`max-score` sums. Omits `owner` and `assignment_type` (the runner stamps them).
  - `render_body(scope: Scope, rows: list[dict], bonus_rows: list[dict], compile_output: str | None) -> str`:
    - `# {label}: {score}/{max}`
    - if `compile_output` is set: `## Your code doesn't compile` and a ```` ```` text ```` fence with its first `COMPILE_LINES` lines
    - `## Koans`: table `| Koan | Points | Result |` with ✅/❌
    - `## What failed`, if any rows failed: per failing row, `<details><summary>{series}.{koan}: {failedAssertions} of {assertions} assertions failed</summary>`, a four-backtick `text` fence holding the message cut to `MESSAGE_LIMIT` (with `\n... (truncated)` when cut), then `</details>`
    - `## Bonus`, if `bonus_rows`: table `| Koan | Result |`
    
    Blocks are added whole. Stop adding failure blocks before the body would exceed `BODY_LIMIT` minus room for the remaining sections, and then append `_Report truncated; see the grade log for the full output._`.

- [ ] **Step 1: Write the failing tests:**
  - `test_scope_milestone`: `resolve_scope("loops", m)` == `Scope("loops", ["AboutLoopsKoans"], [])`.
  - `test_scope_submit`: `resolve_scope("submit/2026-10-29T00-00-00Z-abc1234", m)` has the 9 main series in order and bonus `["AboutArraysKoans", "AboutInterfacesKoans"]`.
  - `test_scope_unknown`: `resolve_scope("nope", m)` raises `ValueError`.
  - `test_result_scores`: two rows (3 assertions passed, 2 assertions failed) → `score == 3`, `max-score == 5`, test names `S.a`/`S.b`, `review` falls back to `COMMIT_URL`.
  - `test_failed_rows`: the manifest rows for one series → all `passed` False, `failedAssertions == assertions`.
  - `test_body_lists_every_failure`: 3 failing rows → `"of"` summaries for all 3, in order.
  - `test_body_compile_error`: `compile_output` of 100 lines → contains `## Your code doesn't compile`, line 40 but not line 41.
  - `test_body_bonus_table`: non-empty `bonus_rows` → contains `## Bonus` and no bonus koan name inside `## Koans`.
  - `test_body_capped` (Review Focus 1): 200 failing rows with 5,000-character messages → `len(body) <= BODY_LIMIT`, ends with the truncation note, and every message block that appears is cut at `MESSAGE_LIMIT`.
  - `test_message_fence_safe` (Review Focus 2): a message containing ```` ``` ```` and `</details>` → the body contains exactly one `## Bonus` heading after it (with bonus rows given), and the message sits between a four-backtick open and close fence.
- [ ] **Step 2: Run `bash classroom50/verify.sh`.** Expected: the new tests fail with an ImportError.
- [ ] **Step 3: Implement the functions** listed in Interfaces in `classroom50/autograder.py`. No `main` yet.
- [ ] **Step 4: Run `bash classroom50/verify.sh`.** Expected: everything passes.
- [ ] **Step 5: Commit.**
  ```bash
  git add classroom50/autograder.py classroom50/tests/test_autograder.py
  git commit -m "feat: build autograder results and release report"
  ```

### Task 7: End-to-end grading, bundle, and local grading

**Files:**
- Modify: `classroom50/autograder.py` (add the runtime functions and `main`)
- Create: `classroom50/grade-local.sh`
- Create: `classroom50/result-v1.schema.json` (copy of `../classroom50/schemas/result-v1.schema.json`)
- Modify: `classroom50/verify.sh` (venv with `jsonschema`)
- Modify: `build.gradle` (tasks `stageClassroomBundle`, `buildClassroomBundle`; `verifyClassroom` depends on `buildClassroomBundle`)
- Test: `classroom50/tests/test_end_to_end.py`

**Interfaces:**
- Consumes: Tasks 5 and 6.
- Produces:
  - Bundle at `build/classroom50/bundle/`: `autograder.py`, `milestones.json`, `koans.json` (Grader `--list` output for all 11 series), `src/engine/**` and `src/sensei/**` from `src/staging/java` (only those two trees: staging also holds solutions, which must never be copied), and `src/engine/Grader.java`. `stageClassroomBundle` is a `Sync` task (`dependsOn syncKoansEngine`). `buildClassroomBundle` is a `JavaExec` task (`dependsOn stageClassroomBundle, classes`; main `engine.Grader`, args `--list <bundle>/koans.json` plus the series read from `milestones.json` with `groovy.json.JsonSlurper`).
  - New `autograder.py` functions: `bundle_dir() -> Path` (`CLASSROOM50_BUNDLE_DIR`, else this file's folder); `java_tool(name: str) -> str` (`$JAVA_HOME/bin/<name>` if set, else `name`); `overlay(bundle_src: Path, checkout_src: Path) -> None` (`rmtree` then `copytree` for `engine` and `sensei`); `compile_sources(src: Path, out: Path) -> tuple[bool, str]`; `run_grader(classes: Path, series: list[str], timeout: int = GRADER_TIMEOUT) -> list[dict]`; `main() -> int`. In `main`, the ref is `GITHUB_REF_NAME`, else `GITHUB_REF` with `refs/tags/` stripped. `main` runs a single Grader call covering scored and bonus series, prints each failing koan's full message to stdout, and writes `result.json` and `release-body.md` into the current directory. It returns 0 on a graded or compile-failed submission and 1 on an unknown ref, a Grader crash, or a timeout.
  - `grade-local.sh <checkout> <ref-name>`: exports `CLASSROOM=local`, `ASSIGNMENT=koans`, `SUBMISSION_TAG=submit/local`, `COMMIT_URL=https://example.invalid/commit`, `RELEASE_URL=https://example.invalid/release`, `GITHUB_REF_NAME=<ref-name>`, and `CLASSROOM50_BUNDLE_DIR` (defaults to `build/classroom50/bundle` resolved from the script's location, overridable), then runs `python3 -I "$CLASSROOM50_BUNDLE_DIR/autograder.py"` with the checkout as the working directory and returns its exit code.
  - `verify.sh`: creates `build/classroom50/venv` if missing, installs `jsonschema` into it, and runs unittest with that interpreter.

- [ ] **Step 1: Write the failing tests** in `test_end_to_end.py`. They grade checkouts from `support.make_checkout` through `grade-local.sh` against the built bundle. Before validating each `result.json` with `jsonschema` against `classroom50/result-v1.schema.json`, add `owner="local"` and `assignment_type="individual"`, the same fields the runner stamps. Also check `score <= max-score` overall and per test. Tests:
  - `test_solved_every_milestone`: for each of the 11 tags, `score == max-score > 0`, all tests passed, and `max-score` equals the sum of `assertions` in `koans.json` for that series.
  - `test_blank_scores_zero`: for `loops`, `objects`, `arrays`, and `submit/verify`: `score == 0`, with `max-score` the same as for solved.
  - `test_broken_scores_zero`: same refs on a broken checkout: `score == 0`, `release-body.md` contains `Your code doesn't compile`, and `max-score` the same as for solved.
  - `test_submit_full_course`: solved, `submit/verify` → test names cover exactly the 9 main series (no `AboutArrays.`/`AboutInterfaces.`), and the body contains `# Full course:` and `## Bonus`.
  - `test_overlay_discards_engine_edits`: a blank checkout plus `src/main/java/engine/Cheat.java` containing `this is not java`; ref `loops` → body has no `doesn't compile`, and `Cheat.java` is gone.
  - `test_unknown_ref_errors`: ref `nope` → nonzero exit, no `result.json`.
- [ ] **Step 2: Run `JAVA_HOME=~/wpilib/2026/jdk ./gradlew verifyClassroom`.** Expected: the new tests fail (no bundle or `main`).
- [ ] **Step 3: Implement** the Gradle tasks, `autograder.py` runtime functions and `main` (with an `if __name__ == "__main__": sys.exit(main())` guard), `grade-local.sh`, the copied schema, and the `verify.sh` venv.
- [ ] **Step 4: Run `JAVA_HOME=~/wpilib/2026/jdk ./gradlew verifyClassroom`.** Expected: all tests pass. Also check `find build/classroom50/bundle -path '*koans/*' -o -path '*bonuses/*'` prints nothing (no solutions in the bundle).
- [ ] **Step 5: Commit.**
  ```bash
  git add classroom50 build.gradle
  git commit -m "feat: grade submissions end to end and build the Classroom 50 bundle"
  ```

### Task 8: Assignment setup, consistency checks, rollout notes

**Files:**
- Create: `classroom50/assignment-setup.sh`, `classroom50/runtime.json`, `classroom50/README.md`
- Test: `classroom50/tests/test_consistency.py`

**Interfaces:**
- Consumes: `milestones.json` (Task 5), `ghsubmit`'s marker block (Task 3), the bundle (Task 7).
- Produces: `assignment-setup.sh <org> <classroom> <slug>`. It holds a `TAGS=(...)` array between `# milestones:begin` / `# milestones:end` markers in the same format as `ghsubmit`, and runs:
  `gh teacher assignment add "$org" "$classroom" "$slug" --name "FRC Java Koans" --template itrt4176/FrcJavaKoans --mode individual --repo-visibility private --submission-mode tag --runtime "<dir>/runtime.json"` plus one `--submission-tag "$t"` per tag. The feedback PR is on by default; leave the flag out. `runtime.json` is `{ "java": "17" }`.

- [ ] **Step 1: Write the failing tests** in `test_consistency.py`:
  - `test_ghsubmit_matches_milestones`: the tags parsed from the marker block in `../FrcJavaKoans/bin/ghsubmit` == `[m["tag"] for m in milestones]`, same order.
  - `test_setup_script_matches_milestones`: same check against `assignment-setup.sh`.
  - `test_series_match_wisdom`: the non-bonus `series` in `milestones.json` equal, in order, the classes listed in `../FrcJavaKoans/src/main/java/sensei/Wisdom.java` (parse `(\w+Koans)\.koans`).
- [ ] **Step 2: Run `JAVA_HOME=~/wpilib/2026/jdk ./gradlew verifyClassroom`.** Expected: the setup-script test fails; the others pass.
- [ ] **Step 3: Write `assignment-setup.sh` and `runtime.json`.** Check the flag names against `../classroom50/wiki/gh-teacher.md` ("assignment add").
- [ ] **Step 4: Write `classroom50/README.md`.** One paragraph on what the directory is. Then: how to run `./gradlew verifyClassroom`, `./gradlew buildClassroomBundle`, and `grade-local.sh` on a `gh teacher download` checkout. Then the spec's Rollout steps 1–6, copied in, and the spec's list of unverified assumptions as a "Check during rollout" list, minus the infinite-loop item that Task 5 now covers.
- [ ] **Step 5: Run `JAVA_HOME=~/wpilib/2026/jdk ./gradlew verifyClassroom run`.** Expected: all tests pass, and the `run` output ends with Task 2's count.
- [ ] **Step 6: Commit.**
  ```bash
  git add classroom50
  git commit -m "feat: add assignment setup script and milestone consistency checks"
  ```
