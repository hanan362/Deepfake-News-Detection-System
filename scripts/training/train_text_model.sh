#!/usr/bin/env bash
# Downloads the GonzaloA/fake_news dataset and the LIAR2 test set, trains four classifiers, evaluates them on a
# held-out split and on LIAR2, and writes the deployed model, its metadata, the registry entry and the metrics.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"
cd "$ROOT"
python ai_models/training/train_text_baseline.py "${1:-all}" "${@:2}"
