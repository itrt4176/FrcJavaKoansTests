# FRC Java Koans on Classroom 50: Design

Date: 2026-10-29
Status: approved in brainstorming, pending written-spec review

## Goal

Run the FRC Java Koans as a Classroom 50 assignment for Iron Tigers (FRC 4176) students. Students work in Tiger Code (`itrt.dev`), submit one koan series at a time, and get a static report of what passed and failed. Nick enters per-series results into Google Classroom and groups series into units there.

Repositories involved:

- `itrt4176/FrcJavaKoans` (the fork): becomes the Classroom 50 template. Student-facing content only.
- `itrt4176/FrcJavaKoansTests`: holds the passing solutions and all grading machinery. To be made private.
- `itrt4176/classroom50` (created by `gh teacher init`): receives the grading bundle. Not yet set up.

## Decisions

| Topic | Decision | Reason |
|---|---|---|
| Assignment structure | One assignment for the whole course | Classroom 50 creates a new student repo per assignment; one repo per student keeps all work in one place. |
| Submission | `submission_mode: tag` with 11 milestone tags (`submission_tags`), one per series | Grading runs only when a student submits a series, which saves Actions minutes. |
| Milestone mechanism | Native milestone tags, moved with force-push on resubmission | Classroom 50 records each attempt on its own minted `submit/<UTC>-<sha>` Release ("via `<milestone>`") and rejects unlisted tags, so we build less. |
| Milestone scope | A milestone grades only its own series | Each Release score is that series' score, ready for Google Classroom. |
| Bonuses | `arrays` and `interfaces` are milestones 10 and 11 | Their scores are separate, so Nick can treat them as extra credit in Google Classroom. Classroom 50 cannot score above max. |
| Plain `submit/*` tag | Grades the 9 main-path series; bonuses appear in the Release body only, unscored | `submit/*` always triggers grading, so it needs a defined meaning. |
| Scoring | One `result.json` row per koan. `max-score` = the koan's assertion count; `score` = that count if every assertion passes, else 0 | Matches how the Sensei judges a koan, weighted by size. |
| Compile errors | Any `javac` failure scores the whole submission 0 | The Sensei cannot run in that state either. |
| Failure report | Every failing koan is reported, not only the first | The Release is a static report card; complete feedback reduces resubmissions and Actions usage. |
| `gh student` extension | Not used | It requires OAuth scopes (`admin:org`, `read:org`, `repo`, `workflow`) and rejects Tiger Code's GitHub App user token (`cli/shared/ghauth/ghauth.go`). |
| Locales | English only; French removed from the fork and the tests repo | The team's course is English. Upstream merges are not expected. |
| Grading code location | Tests repo only; nothing in the template | Keeps the template student-facing and keeps solutions off the public bundle. |
| Spec location | This repo | Kept out of student repos. |

## Milestones

`classroom50/milestones.json` in this repo is the single source of truth:

| Tag | Series (`sensei` class) | Bonus |
|---|---|---|
| `console-and-variables` | `AboutConsoleAndVariablesKoans` | no |
| `methods` | `AboutMethodsKoans` | no |
| `conditions` | `AboutConditionsKoans` | no |
| `more-methods` | `AboutMoreMethodsKoans` | no |
| `decimal-numbers` | `AboutDecimalNumbersKoans` | no |
| `loops` | `AboutLoopsKoans` | no |
| `not7-game` | `AboutNot7GameKoans` | no |
| `classes` | `AboutClassesKoans` | no |
| `objects` | `AboutObjectsKoans` | no |
| `arrays` | `AboutArraysKoans` | yes |
| `interfaces` | `AboutInterfacesKoans` | yes |

Order in the file is Sensei order (`Wisdom.koans`, then bonuses). The same list appears in three other places, all checked against this file by `verifyClassroom`:

1. The bundle copy read by `autograder.py`.
2. The fork's `submit.sh` menu.
3. The `--submission-tag` arguments in `classroom50/assignment-setup.sh`.

## Components

### FrcJavaKoans (template)

1. **French removal.** Delete `koans/french/`, `bonuses/french/`, `FrenchPathToEnlightment.java`, `AideMémoireJava.pdf`, and `release.ps1`. Remove the `fr` value from `engine/text/Locale`, the `fr(...)` texts in `engine/Texts.java`, `sensei/Texts.java`, and `sensei/About*Koans.java`, and `Local.fr` if nothing uses it after that. Keep the `Locale`/`Localizable` plumbing with English as its only value. Update engine tests that use `fr`.
2. **README rewrite.** A new `README.md`, written as assignment instructions, because Tiger Code opens it on first launch. It covers enough to start; the Sensei guides the rest:
   - What the koans are.
   - Accepting the assignment on classroom50.org.
   - Opening the repo in Tiger Code.
   - Running `src/main/java/EnglishPathToEnlightment.java` and reading the Sensei's output.
   - Committing work and submitting a series with `submit.sh`; resubmitting is allowed.
   - Finding results under the repo's Releases.
   - Credits to jletroui's upstream project and its license.
   The Codespaces, zip download, and French sections are removed.
3. **`submit.sh`** (repo root, bash). Interactive:
   1. Shows a numbered menu of the 11 milestones.
   2. Warns and asks for confirmation if there are uncommitted changes.
   3. Pushes the current branch.
   4. Runs `git tag -f <milestone>` and `git push -f origin <milestone>`.
   5. Prints the repo's Releases URL.
   It has no grading logic. README tells students to run `bash submit.sh`, which does not depend on the executable bit.
4. **Devcontainer.** No change for Classroom 50.
5. **Template flag.** Set "Template repository" in GitHub settings (manual, at rollout).

### FrcJavaKoansTests (grading and verification)

1. **English only.** Delete the French solutions in `src/inject/passing/` and make `org.frc.Main` run the English locale only.
2. **`src/main/java/engine/Grader.java`.** In package `engine` because `Koan`'s fields are package-private. Compiles with the synced engine through the existing staging setup.
   - Usage: `java -cp <classes> engine.Grader <out.json> <SeriesClass>...`, where each argument is a `sensei` class name such as `AboutLoopsKoans`; Grader loads `sensei.<name>.koans` by reflection.
   - For each koan: run `TestSensei.execute(koan, Locale.en)`, then emit one row: `series` (student class simple name, for example `AboutLoops`), `koan` (koan name), `assertions` (test count), `failedAssertions`, `passed` (all assertions passed), and `message`. `message` is the captured Sensei output of the first failing assertion, with ANSI escape codes removed, or empty if the koan passed.
   - Writes a JSON array to `<out.json>`, not stdout, so student output cannot corrupt it.
   - Exits 0 when it finishes; any uncaught exception exits nonzero.
3. **`classroom50/autograder.py`.** Python standard library only. Steps:
   1. **Scope.** Read `GITHUB_REF_NAME`. If it is a tag in `milestones.json`, grade that one series. If it starts with `submit/`, grade the 9 main-path series for the score and run the 2 bonus series for the Release body only. Anything else: print an error and exit nonzero.
   2. **Overlay.** Replace `src/main/java/engine/` and `src/main/java/sensei/` in the checkout with the bundle's pristine copies (which include `Grader.java`), removing any other files in those two directories. Leave all other student files untouched.
   3. **Compile.** `javac -d <tmp> <every .java under src/main/java>`. On failure, every in-scope koan row scores 0 with `passed: false`, the report shows the first 40 lines of `javac` output under "Your code doesn't compile", and the script exits 0.
   4. **Grade.** Run Grader with a 300-second timeout. A crash or timeout exits nonzero, which the runner records as `status=error`.
   5. **`result.json`.** Schema `classroom50/result/v1`. One row per scored koan in Sensei order: `test-name` = `<series>.<koan>`, `max-score` = `assertions`, `score` = `assertions` if passed else 0, `passed`, and an extra `message` field. Top-level `score` and `max-score` are the sums. `classroom`, `assignment`, `submission`, `commit`, `release`, and `review` come from the runner's environment (`CLASSROOM`, `ASSIGNMENT`, `SUBMISSION_TAG`, `COMMIT_URL`, `RELEASE_URL`, `REVIEW_URL` falling back to `COMMIT_URL`); the runner stamps `owner`, `assignment_type`, and `datetime` itself.
   6. **`release-body.md`.**
      - Heading with the milestone (or "Full course" for `submit/*`) and the score.
      - Table of every graded koan: koan, points, ✅/❌.
      - "What failed" section: one `<details>` block per failing koan in Sensei order, containing its `message` (cut at 2,000 characters) and "N of M assertions failed".
      - For `submit/*`: a "Bonus" table (koan, ✅/❌), unscored.
      - Total body capped at 100,000 characters; if cut, end with a note pointing to the grade log.
   7. **Grade log.** Print each failing koan's full, uncut `message` to stdout.
4. **`classroom50/milestones.json`.** The table above as JSON: an ordered array of `{ "tag", "series", "bonus" }`.
5. **`classroom50/grade-local.sh <checkout> <ref-name>`.** Sets the runner's environment variables with placeholder URLs (`CLASSROOM`, `ASSIGNMENT`, `SUBMISSION_TAG`, `COMMIT_URL`, `RELEASE_URL`, `GITHUB_REF_NAME`, `CLASSROOM50_BUNDLE_DIR`) and runs the bundled `autograder.py` inside `<checkout>`. Used by `verifyClassroom` and for regrading repos downloaded with `gh teacher download`.
6. **`classroom50/assignment-setup.sh <org> <classroom> <slug>`.** Runs `gh teacher assignment add` with: `--template itrt4176/FrcJavaKoans`, `--submission-mode tag`, one `--submission-tag` per milestone, and `--runtime` pointing to `classroom50/runtime.json` (`{ "java": "17" }`). Also: individual mode, private repositories, autograded, feedback PR on. Verify exact flag names against `classroom50/wiki/gh-teacher.md` when writing it.
7. **`classroom50/result-v1.schema.json`.** A vendored copy of Classroom 50's `schemas/result-v1.schema.json`, used only by verification.
8. **Gradle `buildClassroomBundle`.** Depends on `syncKoansEngine`. Produces `build/classroom50/bundle/` containing `autograder.py`, `milestones.json`, and `src/engine/` + `src/sensei/` (synced engine and sensei plus `Grader.java`). The overlay in `autograder.py` copies from `src/`.
9. **Gradle `verifyClassroom`.** Depends on `buildClassroomBundle`. See Testing.

## Data flow

1. Student runs `bash submit.sh`, picks `loops`; `loops` is force-pushed.
2. The student repo's `autograde.yaml` (written by Classroom 50 at accept) fires on the `loops` tag push.
3. Classroom 50's runner mints `submit/<UTC>-<sha>`, sets up JDK 17, downloads the bundle, and runs `autograder.py` in the checkout with `GITHUB_REF_NAME=loops`.
4. `autograder.py` overlays, compiles, runs Grader on `AboutLoopsKoans`, and writes `result.json` and `release-body.md`.
5. The runner publishes the Release "Submission submit/... (via loops)" and sets the `classroom50/autograde` commit status: success if every row passed.
6. Nick runs Collect in Classroom 50 and reads per-series results from Releases, the submissions history, or `gh teacher download`, then enters them in Google Classroom.

## Error handling

| Situation | Result |
|---|---|
| Student code doesn't compile | Score 0 for every koan in scope; report shows `javac` errors; status failure. |
| Koan fails | Row scores 0; report includes its Sensei message. |
| Student code loops forever | Engine's own loop detection, then the 300-second Grader timeout → `status=error`. |
| Grader crashes | `autograder.py` exits nonzero → runner records `status=error`. |
| Unknown ref name reaches the autograder | Exit nonzero → `status=error`. Should not happen: the runner skips unlisted tags. |
| Student edits `engine/` or `sensei/` | Overwritten by the pristine overlay before compiling. |
| Student edits the workflow or forges a Release | Not prevented (Classroom 50 limitation). Trusted scores come from `gh teacher download` + `grade-local.sh`. |
| Report too long | Per-koan messages cut at 2,000 characters, body at 100,000; full output in the grade log. |

## Testing

- **Fork engine tests.** `engine.test.runner.TestRunner` passes under the WPILib JDK 17 after the French removal. Record the new expected count in the workspace CLAUDE.md (currently 185/185).
- **`submit.sh` test.** A bash test using a temporary repo with a bare remote: the chosen tag is created and pushed; a second run moves it with `-f`.
- **`./gradlew run`.** English-only solutions check passes. Record the new expected count in the workspace CLAUDE.md (currently 512/512 in 162 koans).
- **`./gradlew verifyClassroom`.** For each of the 11 milestones and for `submit/verify`, run `grade-local.sh` against three checkouts built in `build/`:
  - **Solved** (fork `src/main/java` overlaid with `src/inject/passing/`): `score == max-score`, every row passed.
  - **Blank** (fork as-is): `score == 0`.
  - **Broken** (blank plus one file with a syntax error): `score == 0` and `release-body.md` contains "doesn't compile".

  Every `result.json` is validated against `classroom50/result-v1.schema.json` with `jsonschema` in a throwaway venv under `build/`, and checked for `score <= max-score` overall and per row. The task also fails if `submit.sh`'s menu (read from `../FrcJavaKoans/submit.sh`) or `assignment-setup.sh`'s tags differ from `milestones.json`.

## Rollout (manual, by Nick)

1. Make `itrt4176/FrcJavaKoansTests` private.
2. Mark `itrt4176/FrcJavaKoans` as a template repository.
3. Set up Classroom 50 in `itrt4176` (`gh teacher init`) and create a classroom.
4. Run `./gradlew buildClassroomBundle` and copy `build/classroom50/bundle/*` to `itrt4176/classroom50/<classroom>/autograders/<slug>/`.
5. Run `classroom50/assignment-setup.sh itrt4176 <classroom> <slug>`.
6. With a test student account:
   - Accept the assignment and open the repo in Tiger Code.
   - Run `submit.sh`, then resubmit the same milestone; confirm the force-pushed tag works with the Tiger Code token and each attempt gets its own Release titled "via `<milestone>`".
   - Run Regrade on that repo and confirm the regraded result still grades the milestone's series (that `GITHUB_REF_NAME` survives a re-run).

## Unverified assumptions

- `GITHUB_REF_NAME` is the milestone tag on a Regrade re-run. If it is not, Regrade of milestone submissions grades the wrong scope; fallback is to read the trigger from the Release title or to tell students to resubmit.
- Tiger Code's GitHub App token can force-push tags (Contents: write).
- GitHub's Release body limit (about 125,000 characters) is above the 100,000-character cap.
- The engine detects infinite loops in student code.
- The number of engine tests and solution assertions that disappear with French.

## Out of scope

- Per-series due dates, late flags, or gradebook columns in Classroom 50 (one assignment has one `due`).
- Syncing scores to Google Classroom.
- Self-hosted runners.
- Changes to how the Sensei runs or to koan content.
- Any change in the `classroom50/` reference clone.
