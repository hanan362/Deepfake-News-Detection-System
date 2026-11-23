#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
cd "$ROOT/backend"
python -m app.db.migrate
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
