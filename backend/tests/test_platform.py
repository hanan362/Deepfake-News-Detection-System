"""Dashboard, feedback, admin area, module status and general API behaviour."""
import pytest

from app.db.session import SessionLocal
from app.ml.text_detection.service import get_detector
from app.models import UserFeedback

from .conftest import API, ARTICLE, make_image_bytes

needs_model = pytest.mark.skipif(not get_detector().available, reason="text model not trained")


@needs_model
def test_dashboard_numbers_are_counted_from_the_database(client, alice, bob):
    for _ in range(2):
        client.post(f"{API}/analysis/text", json={"text": ARTICLE}, headers=alice.headers)
    client.post(f"{API}/analysis/image", files={"file": ("a.jpg", make_image_bytes(), "image/jpeg")}, headers=alice.headers)
    client.post(f"{API}/analysis/text", json={"text": ARTICLE}, headers=bob.headers)
    s = client.get(f"{API}/dashboard/stats", headers=alice.headers).json()
    assert s["total_analyses"] == 3 and s["by_type"] == {"text": 2, "image": 1}
    assert sum(s["by_verdict"].values()) == 3
    assert len(s["daily"]) == 14 and sum(d["count"] for d in s["daily"]) == 3 and s["daily"][-1]["count"] == 3
    assert len(s["recent"]) == 3
    assert client.get(f"{API}/dashboard/stats", headers=bob.headers).json()["total_analyses"] == 1


def test_empty_dashboard_is_zeroes_not_demo_data(client, alice):
    s = client.get(f"{API}/dashboard/stats", headers=alice.headers).json()
    assert s["total_analyses"] == 0 and s["by_type"] == {} and s["recent"] == [] and all(d["count"] == 0 for d in s["daily"])


def test_video_endpoint_needs_login(client):
    assert client.post(f"{API}/analysis/video").status_code == 401


def test_model_registry_is_honest(client, admin):
    r = client.get(f"{API}/models", headers=admin.headers)
    assert r.status_code == 200
    by_module = {m["module"]: m for m in r.json()["models"]}
    assert set(by_module) == {"text", "text_ur", "image", "video", "multimodal", "evidence", "url"}
    assert by_module["text_ur"]["status"] in {"experimental", "unavailable"}  # never presented as a validated model
    assert by_module["image"]["status"] == "heuristic"
    assert by_module["video"]["status"] in {"experimental", "heuristic", "unavailable"}  # a baseline, never presented as validated
    assert by_module["multimodal"]["status"] in {"pretrained", "heuristic", "unavailable"}
    assert by_module["evidence"]["status"] in {"pretrained", "heuristic", "unavailable"}
    assert by_module["url"]["status"] in {"heuristic", "unavailable"}  # rule-based checks, never a trained model
    assert by_module["text"]["status"] in {"trained_baseline", "unavailable"}
    assert set(r.json()["status_meanings"]) >= {"trained_baseline", "planned", "heuristic"}


def test_health(client):
    h = client.get(f"{API}/health").json()
    assert h["status"] == "ok" and h["database"] == "ok"


@needs_model
def test_feedback_flow(client, alice, bob, admin):
    a = client.post(f"{API}/analysis/text", json={"text": ARTICLE}, headers=alice.headers).json()["id"]
    r = client.post(f"{API}/feedback", json={"category": "incorrect_result", "message": "The result looks wrong.", "analysis_id": a}, headers=alice.headers)
    assert r.status_code == 201 and r.json()["status"] == "new"
    assert client.post(f"{API}/feedback", json={"category": "bug", "message": "x"}, headers=alice.headers).status_code == 422
    assert client.post(f"{API}/feedback", json={"category": "nonsense", "message": "long enough"}, headers=alice.headers).status_code == 422
    assert client.post(f"{API}/feedback", json={"category": "bug", "message": "valid message", "analysis_id": a}, headers=bob.headers).status_code == 404
    assert len(client.get(f"{API}/feedback", headers=alice.headers).json()) == 1
    assert client.get(f"{API}/feedback", headers=bob.headers).json() == []
    fid = r.json()["id"]
    assert client.patch(f"{API}/admin/feedback/{fid}", json={"status": "reviewed"}, headers=alice.headers).status_code == 403
    done = client.patch(f"{API}/admin/feedback/{fid}", json={"status": "reviewed"}, headers=admin.headers).json()
    assert done["status"] == "reviewed" and done["username"] == "alice"
    assert client.get(f"{API}/admin/feedback?status=new", headers=admin.headers).json() == []
    with SessionLocal() as db:
        assert db.get(UserFeedback, fid).reviewed_by == admin.id


def test_admin_routes_require_admin(client, alice):
    paths = ["stats", "users", "feedback", "audit-logs", "models"]
    for p in paths:
        assert client.get(f"{API}/admin/{p}").status_code == 401
        assert client.get(f"{API}/admin/{p}", headers=alice.headers).status_code == 403


def test_admin_stats_users_and_audit_log(client, alice, admin):
    s = client.get(f"{API}/admin/stats", headers=admin.headers).json()
    assert s["users"]["total"] == 2 and s["users"]["admins"] == 1 and s["analyses"]["total"] == 0
    users = client.get(f"{API}/admin/users?q=ali", headers=admin.headers).json()
    assert users["total"] == 1 and users["items"][0]["username"] == "alice" and "hashed_password" not in str(users)
    logs = client.get(f"{API}/admin/audit-logs?action=auth.login", headers=admin.headers).json()
    assert logs["total"] == 2 and {i["user"] for i in logs["items"]} == {"alice", "root"}
    assert client.get(f"{API}/admin/models", headers=admin.headers).json()["registry"]


def test_admin_can_change_roles_but_not_lock_themselves_out(client, alice, admin):
    assert client.patch(f"{API}/admin/users/{alice.id}", json={"role": "admin"}, headers=admin.headers).json()["role"] == "admin"
    assert client.patch(f"{API}/admin/users/{admin.id}", json={"role": "user"}, headers=admin.headers).status_code == 400
    assert client.patch(f"{API}/admin/users/{admin.id}", json={"is_active": False}, headers=admin.headers).status_code == 400
    assert client.patch(f"{API}/admin/users/9999", json={"role": "user"}, headers=admin.headers).status_code == 404
    assert client.patch(f"{API}/admin/users/{alice.id}", json={"role": "superuser"}, headers=admin.headers).status_code == 422


def test_admin_user_management_is_audited(client, alice, admin):
    client.patch(f"{API}/admin/users/{alice.id}", json={"is_active": False}, headers=admin.headers)
    logs = client.get(f"{API}/admin/audit-logs?action=admin.update_user", headers=admin.headers).json()
    assert logs["total"] == 1 and logs["items"][0]["detail"] == {"is_active": False}


def test_errors_use_one_consistent_envelope(client, alice):
    r = client.get(f"{API}/nothing-here")
    assert r.status_code == 404 and set(r.json()["error"]) == {"code", "message", "details"}
    r = client.post(f"{API}/auth/login", json={})
    assert r.status_code == 422 and r.json()["error"]["details"]
    assert client.get(f"{API}/users/me").json()["error"]["code"] == "UNAUTHENTICATED"


def test_security_headers_and_cors(client):
    r = client.get(f"{API}/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get(f"{API}/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_openapi_docs_are_available(client):
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    assert "/api/v1/analysis/text" in spec["paths"] and "/api/v1/auth/login" in spec["paths"]


def test_models_endpoint_exposes_the_real_input_limits(client, admin):
    from app.core.config import get_settings
    s = get_settings()
    limits = client.get(f"{API}/models", headers=admin.headers).json()["limits"]
    assert limits["min_text_words"] == s.min_text_tokens and limits["max_image_mb"] == s.max_image_mb
    public = client.get(f"{API}/modules").json()["limits"]
    assert public["min_text_words"] == s.min_text_tokens and public["max_image_mb"] == s.max_image_mb


@needs_model
def test_evaluation_endpoint_returns_the_measured_numbers(client, admin):
    body = client.get(f"{API}/models/text/evaluation", headers=admin.headers).json()
    comp = body["evaluation"]["comparison"]
    assert set(comp) == {"logistic_regression", "naive_bayes", "linear_svm", "random_forest"}
    lr = comp["logistic_regression"]
    # the point of the cross-dataset check: a big gap between in-distribution and external performance
    assert lr["test"]["roc_auc"] > 0.9 and lr["external_liar2"]["roc_auc"] < 0.7
    assert body["dataset"]["rows_clean"]["train"] > 20000 and body["dataset"]["external_test_set"]["name"] == "liar2_test"


TECHNICAL_ENDPOINTS = ["/models", "/models/text/evaluation", "/models/text-ur/evaluation", "/models/evidence/evaluation", "/models/video/evaluation"]


@pytest.mark.parametrize("path", TECHNICAL_ENDPOINTS)
def test_technical_endpoints_are_for_administrators_only(client, alice, admin, path):
    """The model registry and the measured evaluation are enforced on the server, not only hidden in the interface."""
    assert client.get(f"{API}{path}").status_code == 401
    r = client.get(f"{API}{path}", headers=alice.headers)
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"
    assert client.get(f"{API}{path}", headers=admin.headers).status_code in (200, 404)  # 404 only if that evaluation was never run


def test_the_public_module_list_says_what_runs_and_nothing_technical(client):
    r = client.get(f"{API}/modules")
    assert r.status_code == 200
    body = r.json()
    assert {m["module"] for m in body["models"]} == {"text", "text_ur", "image", "video", "multimodal", "evidence", "url"}
    for m in body["models"]:
        assert set(m) == {"module", "status", "description"}  # no model name, version, algorithm, limitations or metrics
    assert set(body["limits"]) >= {"min_text_words", "max_text_chars", "max_image_mb", "max_video_mb", "text_languages"}
    assert "text_confidence_threshold" not in body["limits"] and "status_meanings" not in body
    blob = r.text.lower()
    for word in ("roc", "joblib", "liar2", "tf-idf", "logistic", "clip", "bend the truth", "gonzalo"):
        assert word not in blob, word
