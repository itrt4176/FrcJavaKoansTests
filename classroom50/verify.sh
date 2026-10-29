#!/usr/bin/env bash
# Run the Classroom 50 verification tests from the repo root.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s classroom50 -t .
