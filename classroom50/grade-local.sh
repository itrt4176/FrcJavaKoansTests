#!/usr/bin/env bash
# Grade a student checkout locally the way the Classroom 50 runner does.
# Usage: grade-local.sh <checkout> <ref-name>
#   <ref-name> is a milestone tag (e.g. loops) or a submit/* tag.
# Writes result.json and release-body.md into <checkout>; exits with the
# autograder's status. Set CLASSROOM50_BUNDLE_DIR to grade with another bundle.
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <checkout> <ref-name>" >&2
    exit 2
fi

script_dir="$(cd "$(dirname "$0")" && pwd)"
checkout="$1"

export CLASSROOM=local
export ASSIGNMENT=koans
export SUBMISSION_TAG=submit/local
export COMMIT_URL=https://example.invalid/commit
export RELEASE_URL=https://example.invalid/release
export GITHUB_REF_NAME="$2"
export CLASSROOM50_BUNDLE_DIR="${CLASSROOM50_BUNDLE_DIR:-$script_dir/../build/classroom50/bundle}"
CLASSROOM50_BUNDLE_DIR="$(cd "$CLASSROOM50_BUNDLE_DIR" && pwd)"

cd "$checkout"
status=0
python3 -I "$CLASSROOM50_BUNDLE_DIR/autograder.py" || status=$?
exit "$status"
