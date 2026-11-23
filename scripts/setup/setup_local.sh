#!/usr/bin/env bash
# One-time setup for running the project without Docker (Linux, macOS, WSL).
# Needs Python 3.10+ and Node.js 20+. Run from anywhere:  bash scripts/setup/setup_local.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "==> Python environment (.venv)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

echo "==> Settings (.env)"
[ -f .env ] || cp .env.example .env

echo "==> Database"
(cd backend && python -m app.db.migrate)

echo "==> Frontend packages"
(cd frontend && npm ci)

cat <<MSG

Setup finished. Two more steps:

  1. Train the text model (about 10 to 20 minutes, needs internet once to download the dataset):
       bash scripts/training/train_text_model.sh
     Until you do, the Text module reports itself as unavailable. Nothing is faked.

  2. Start the app in two terminals:
       bash scripts/run_backend.sh      # http://127.0.0.1:8000/docs
       bash scripts/run_frontend.sh     # http://localhost:5173

MSG
