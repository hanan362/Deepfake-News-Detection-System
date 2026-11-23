"""docs/api/openapi.json is the committed description of the API. If an endpoint changes and the file is not refreshed
(python scripts/maintenance/export_openapi.py), this test fails, so the documentation cannot silently go stale.

Only the parts that describe the contract are compared (routes, methods, summaries, authentication, parameters, status
codes). The exact JSON-schema wording differs between pydantic versions and is not part of the contract."""
import json
from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[2]


def _contract(spec: dict) -> dict:
    out = {}
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            out[f"{method.upper()} {path}"] = {
                "summary": op.get("summary"),
                "secured": bool(op.get("security")),
                "parameters": sorted(p["name"] for p in op.get("parameters", [])),
                "body": sorted((op.get("requestBody") or {}).get("content", {})),
                "responses": sorted(op["responses"]),
            }
    return out


def test_committed_openapi_matches_the_application():
    committed = json.loads((ROOT / "docs" / "api" / "openapi.json").read_text(encoding="utf-8"))
    assert _contract(committed) == _contract(app.openapi()), "Run: python scripts/maintenance/export_openapi.py"
