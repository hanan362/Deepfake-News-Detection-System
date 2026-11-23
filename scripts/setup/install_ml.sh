#!/usr/bin/env bash
# Installs the optional machine-learning packages (torch, transformers, opencv). Needed for the evidence stance model, the
# CLIP image-text check and the video classifier. About 700 MB. Without them those parts say what is missing.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"
cd "$ROOT"
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements-ml.txt
# Fetch the pretrained models now (about 1 GB) so the first analysis on each page is not slow. SKIP_MODELS=1 skips this
# step. A failed download does not fail the install: each model is then fetched the first time its page is used.
if [ "${SKIP_MODELS:-0}" != "1" ]; then
  python scripts/setup/download_models.py || echo "Some models were not downloaded. Run scripts/setup/download_models.sh later."
fi
