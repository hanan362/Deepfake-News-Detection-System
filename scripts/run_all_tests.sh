#!/usr/bin/env bash
# Runs every automated check and prints a pass/fail line for each. Needs the setup script to have run, and the text model
# to be trained (the end-to-end tests analyse a real article with it).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"
export E2E_PYTHON="${E2E_PYTHON:-python}"
fail=0
run() { local name="$1"; shift; echo "==> $name"; if "$@"; then echo "PASS  $name"; else echo "FAIL  $name"; fail=1; fi; }

run "backend tests (pytest)"            bash -c "cd '$ROOT/backend' && python -m pytest -q"
run "frontend type check"               bash -c "cd '$ROOT/frontend' && npm run typecheck"
run "frontend unit tests (vitest)"      bash -c "cd '$ROOT/frontend' && npm test"
run "frontend production build"         bash -c "cd '$ROOT/frontend' && npm run build"
run "end-to-end tests (playwright)"     bash -c "cd '$ROOT/frontend' && npx playwright test"
exit $fail
