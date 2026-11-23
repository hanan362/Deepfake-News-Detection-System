#!/usr/bin/env bash
# Downloads the three small video samples (about 350 MB) and measures the video frame model on them.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"
cd "$ROOT"
python ai_models/training/prepare_video_data.py
python ai_models/training/evaluate_video.py --write-registry "$@"
