"""Write the API description (OpenAPI 3) to docs/api/openapi.json.

Usage: python scripts/maintenance/export_openapi.py
Run it after changing an endpoint. A test fails if the committed file no longer matches the application.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
# Use a throw-away database so exporting never touches real data.
_tmp = tempfile.mkdtemp(prefix="openapi-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp}/x.db")
os.environ.setdefault("STORAGE_DIR", f"{_tmp}/storage")
os.environ.setdefault("SECRET_KEY", "export-only-secret-key-0123456789-abcdefghijklmnop")

from app.main import app  # noqa: E402


def main() -> None:
    out = ROOT / "docs" / "api" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
