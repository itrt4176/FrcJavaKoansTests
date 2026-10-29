#!/usr/bin/env bash
# Register the FRC Java Koans assignment in a Classroom 50 classroom.
# Usage: assignment-setup.sh <org> <classroom> <slug>
set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "usage: $0 <org> <classroom> <slug>" >&2
    exit 2
fi
org=$1
classroom=$2
slug=$3

dir=$(cd "$(dirname "$0")" && pwd)

# Keep in sync with bin/ghsubmit in FrcJavaKoans and with milestones.json
# (checked by classroom50/tests/test_consistency.py).
# milestones:begin
TAGS=(
  console-and-variables
  methods
  conditions
  more-methods
  decimal-numbers
  loops
  not7-game
  classes
  objects
  arrays
  interfaces
)
# milestones:end

args=()
for t in "${TAGS[@]}"; do
    args+=(--submission-tag "$t")
done

gh teacher assignment add "$org" "$classroom" "$slug" \
    --name "FRC Java Koans" \
    --template itrt4176/FrcJavaKoans \
    --mode individual \
    --repo-visibility private \
    --submission-mode tag \
    --runtime "$dir/runtime.json" \
    "${args[@]}"
