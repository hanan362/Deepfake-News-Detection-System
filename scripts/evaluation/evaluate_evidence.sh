#!/usr/bin/env bash
# Measures the evidence stance model on FEVER gold evidence (downloads about 15 MB).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"
cd "$ROOT"
python ai_models/training/evaluate_evidence_nli.py "$@"
