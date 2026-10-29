#!/usr/bin/env bash
# Run the Classroom 50 verification tests from the repo root.
# Uses a throwaway venv under build/ that has jsonschema installed.
set -euo pipefail
cd "$(dirname "$0")/.."
venv=build/classroom50/venv
if [ ! -x "$venv/bin/python" ]; then
    python3 -m venv "$venv"
fi
"$venv/bin/python" -m pip install --quiet --disable-pip-version-check jsonschema
"$venv/bin/python" -m unittest discover -s classroom50 -t .
