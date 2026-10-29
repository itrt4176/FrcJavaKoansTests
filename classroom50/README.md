# Classroom 50 support for FRC Java Koans

This directory holds everything the Iron Tigers need to run the FRC Java Koans as a Classroom 50 assignment: the custom `autograder.py` and its `milestones.json` (milestone tag to koan series), the assignment registration script `assignment-setup.sh` with its `runtime.json`, local grading and verification scripts, and the tests for all of it. Students submit a milestone with `ghsubmit` (in the `FrcJavaKoans` fork), which pushes a tag; the autograder grades that milestone's series.

## Running things

- `./gradlew verifyClassroom` runs all the Classroom 50 tests (grader, autograder, `ghsubmit`, end to end, and the consistency checks). It builds the bundle first and installs `jsonschema` in a throwaway venv under `build/`.
- `./gradlew buildClassroomBundle` writes the autograder bundle to `build/classroom50/bundle/`.
- `classroom50/grade-local.sh <checkout> <ref-name>` grades a student checkout locally, where `<ref-name>` is a milestone tag (for example `loops`) or a `submit/...` tag. A checkout fetched with `gh teacher download <org> <classroom> <assignment>` sits at the student's latest commit, so first check out the commit of the milestone you want to grade (for example `git -C <checkout> checkout loops`).

Use `JAVA_HOME=~/wpilib/2026/jdk` for Gradle.

## Rollout (manual, by Nick)

1. Make `itrt4176/FrcJavaKoansTests` private.
2. Mark `itrt4176/FrcJavaKoans` as a template repository.
3. Set up Classroom 50 in `itrt4176` (`gh teacher init`) and create a classroom.
4. With the sibling `../FrcJavaKoans` checked out at the template's commit (`master` after the branch is merged), run `./gradlew buildClassroomBundle` and copy `build/classroom50/bundle/*` to `itrt4176/classroom50/<classroom>/autograders/<slug>/`. The bundle copies `engine/` and `sensei/` from whatever is checked out in `../FrcJavaKoans`, so any later change to the fork's `engine/` or `sensei/` needs a rebuild and a recopy of the bundle.
5. Run `classroom50/assignment-setup.sh itrt4176 <classroom> <slug>`.
6. With a test student account:
   - Accept the assignment and open the repo in Tiger Code.
   - Run `ghsubmit` from a new Tiger Code terminal (confirms the `PATH` entry), then resubmit the same milestone; confirm the force-pushed tag works with the Tiger Code token and each attempt gets its own Release titled "via `<milestone>`".
   - Run Regrade on that repo and confirm the regraded result still grades the milestone's series (that `GITHUB_REF_NAME` survives a re-run).
   - Open a fresh Tiger Code workspace, wait for the Java import to finish, and confirm `bin/ghsubmit` still exists and `git status` is clean.

## Check during rollout

- `GITHUB_REF_NAME` is the milestone tag on a Regrade re-run. Reading Classroom 50's `regrade_repos.py` shows Regrade re-runs the latest graded run through the Actions rerun API, and a re-run keeps the original run's ref, so this should hold; it is still a live check. If it is not, Regrade of milestone submissions grades the wrong scope; fallback is to read the trigger from the Release title or to tell students to resubmit.
- Tiger Code's GitHub App token can force-push tags (Contents: write).
- GitHub's Release body limit (about 125,000 characters) is above the 100,000-character cap.
- Tiger Code applies `remoteEnv` and expands `${containerWorkspaceFolder}`, and the template copy keeps `ghsubmit`'s executable bit.

## Known limitations

- Koans run in-process in the Grader JVM, so a determined student could forge results with code in their koan files. This is inherent to running student code in-process; the pristine overlay protects only `engine/` and `sensei/`.
- The assignment is tag-only: a branch push is an unknown ref and makes the autograder exit 1.
- Koans that read stdin have no per-koan time limit; only the 300-second Grader timeout bounds them.
- Student code that calls `System.exit` ends the Grader before it writes its output, so the autograder exits 1 without a `result.json` and the run ends with an error instead of a report.
- Regrade re-runs only each repo's latest submission, and GitHub refuses to re-run runs older than about a month (Regrade skips those repos). A grader fix therefore does not refresh earlier milestones; regrade those with `gh teacher download` plus `grade-local.sh`, or ask students to resubmit.
- `verify.sh` needs python3's venv module (`python3-venv` on Debian/Ubuntu) and network access the first time, to install `jsonschema`.
