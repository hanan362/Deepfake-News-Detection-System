#!/usr/bin/env bash
# Measures the CLIP image-text check on Flickr30k and writes its thresholds (downloads about 30 MB).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"
cd "$ROOT"
python ai_models/training/evaluate_clip_consistency.py "$@"
