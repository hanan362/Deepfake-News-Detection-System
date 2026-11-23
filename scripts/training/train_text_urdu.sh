#!/usr/bin/env bash
# Downloads the Urdu "Bend the Truth" fake-news dataset, runs pair-aware cross-validation, trains the experimental Urdu
# model and writes its checkpoint, registry entry, metrics and dataset manifest. Needs no GPU and about a minute.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"
cd "$ROOT"
python ai_models/training/train_text_urdu.py "$@"
