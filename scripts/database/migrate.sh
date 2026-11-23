#!/usr/bin/env bash
# Apply database migrations to whatever DATABASE_URL points at (default: the SQLite file in storage/).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"
cd "$ROOT/backend"
python -m app.db.migrate
alembic current
