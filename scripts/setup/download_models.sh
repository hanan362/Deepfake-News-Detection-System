#!/usr/bin/env bash
# Downloads the pretrained models (CLIP, the evidence NLI model, the video frame classifier) once, about 1 GB in total, so
# that the first analysis on each page does not wait for them. Usage: download_models.sh [clip] [nli] [video]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"
cd "$ROOT"
python scripts/setup/download_models.py "$@"
