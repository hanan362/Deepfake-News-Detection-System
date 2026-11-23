import jwt

from app.core.config import get_settings
from app.core.security import hash_password, validate_password_strength, verify_password
from app.db.session import SessionLocal
from app.models import AuditLog, PasswordResetToken, User

from .conftest import API


def register(client, **over):
    body = {"email": "carol@example.com", "username": "carol", "password": "Passw0rd1", **over}
    return client.post(f"{API}/auth/register", json=body)


def test_register_creates_user_and_hashes_password(client):
    r = register(client)
    assert r.status_code == 201
    assert r.json()["role"] == "user" and "password" not in r.text and "hashed" not in r.text
    with SessionLocal() as db:
        stored = db.query(User).one().hashed_password
    assert stored != "Passw0rd1" and stored.startswith("$2") and verify_password("Passw0rd1", stored)


def test_duplicate_email_and_username_are_rejected_case_insensitively(client):
    assert register(client).status_code == 201
    assert register(client, email="CAROL@example.com", username="other").status_code == 409
    assert register(client, email="x@example.com", username="CAROL").status_code == 409


def test_weak_or_invalid_input_is_rejected(client):
    for body in ({"password": "short1"}, {"password": "allletters"}, {"password": "12345678"}, {"email": "not-an-email"},
                 {"username": "a b"}, {"password": "a1" * 40}):
        r = register(client, **body)
        assert r.status_code == 422, body
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_password_rules_unit():
    assert validate_password_strength("Passw0rd1") is None
    assert validate_password_strength("x" * 73 + "1a") is not None
    assert verify_password("nope", "not-a-hash") is False
    assert verify_password("Passw0rd1", hash_password("Passw0rd1"))


def test_login_with_email_or_username(client, alice):
    for ident in ("alice", "ALICE@example.com"):
        r = client.post(f"{API}/auth/login", json={"identifier": ident, "password": alice.password})
        assert r.status_code == 200 and r.json()["user"]["username"] == "alice"
        assert r.json()["token_type"] == "bearer"


def test_wrong_password_and_unknown_user_give_the_same_error(client, alice):
    a = client.post(f"{API}/auth/login", json={"identifier": "alice", "password": "wrong"})
    b = client.post(f"{API}/auth/login", json={"identifier": "ghost", "password": "wrong"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"] == b.json()["error"]


def test_protected_routes_need_a_valid_token(client, alice):
    assert client.get(f"{API}/users/me").status_code == 401
    assert client.get(f"{API}/users/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    forged = jwt.encode({"sub": str(alice.id), "jti": "x", "pv": 0, "exp": 9999999999}, "wrong-secret", algorithm="HS256")
    assert client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    assert client.get(f"{API}/users/me", headers=alice.headers).json()["username"] == "alice"


def test_logout_really_ends_the_session(client, alice):
    assert client.post(f"{API}/auth/logout", headers=alice.headers).status_code == 200
    r = client.get(f"{API}/users/me", headers=alice.headers)
    assert r.status_code == 401


def test_disabled_account_cannot_log_in_or_use_old_token(client, alice, admin):
    assert client.patch(f"{API}/admin/users/{alice.id}", json={"is_active": False}, headers=admin.headers).status_code == 200
    assert client.get(f"{API}/users/me", headers=alice.headers).status_code == 401
    r = client.post(f"{API}/auth/login", json={"identifier": "alice", "password": alice.password})
    assert r.status_code == 403 and r.json()["error"]["code"] == "ACCOUNT_DISABLED"


def test_forgot_password_does_not_reveal_whether_an_account_exists(client, alice):
    known = client.post(f"{API}/auth/forgot-password", json={"email": alice.email})
    unknown = client.post(f"{API}/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]
    assert known.json()["reset_token"] and unknown.json()["reset_token"] is None  # token exposed only in dev/test mode


def test_reset_token_is_stored_hashed_not_plain(client, alice):
    token = client.post(f"{API}/auth/forgot-password", json={"email": alice.email}).json()["reset_token"]
    with SessionLocal() as db:
        row = db.query(PasswordResetToken).one()
    assert row.token_hash != token and len(row.token_hash) == 64


def test_password_reset_flow_is_single_use_and_ends_old_sessions(client, alice):
    token = client.post(f"{API}/auth/forgot-password", json={"email": alice.email}).json()["reset_token"]
    assert client.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "BrandNew123"}).status_code == 200
    assert client.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "Another1234"}).status_code == 400
    assert client.get(f"{API}/users/me", headers=alice.headers).status_code == 401  # old session ended
    assert client.post(f"{API}/auth/login", json={"identifier": "alice", "password": alice.password}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"identifier": "alice", "password": "BrandNew123"}).status_code == 200


def test_reset_rejects_unknown_expired_and_weak(client, alice):
    assert client.post(f"{API}/auth/reset-password", json={"token": "x" * 30, "new_password": "BrandNew123"}).status_code == 400
    token = client.post(f"{API}/auth/forgot-password", json={"email": alice.email}).json()["reset_token"]
    assert client.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "weak"}).status_code == 422
    from datetime import datetime, timedelta, timezone
    with SessionLocal() as db:
        row = db.query(PasswordResetToken).one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert client.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "BrandNew123"}).status_code == 400


def test_reset_token_is_not_exposed_when_setting_is_off(client, alice):
    s = get_settings()
    s.expose_reset_token = False
    try:
        r = client.post(f"{API}/auth/forgot-password", json={"email": alice.email})
        assert r.json()["reset_token"] is None
    finally:
        s.expose_reset_token = True


def test_change_password(client, alice):
    r = client.post(f"{API}/users/me/password", json={"current_password": "wrong", "new_password": "NewPassw0rd"}, headers=alice.headers)
    assert r.status_code == 400
    r = client.post(f"{API}/users/me/password", json={"current_password": alice.password, "new_password": "NewPassw0rd"}, headers=alice.headers)
    assert r.status_code == 200
    assert client.get(f"{API}/users/me", headers=alice.headers).status_code == 401  # old token no longer valid
    fresh = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get(f"{API}/users/me", headers=fresh).status_code == 200  # the token returned by the call works


def test_profile_update_and_username_conflict(client, alice, bob):
    r = client.patch(f"{API}/users/me", json={"full_name": "  Alice A  "}, headers=alice.headers)
    assert r.status_code == 200 and r.json()["full_name"] == "Alice A"
    assert client.patch(f"{API}/users/me", json={"username": "bob"}, headers=alice.headers).status_code == 409
    assert client.patch(f"{API}/users/me", json={"username": "alice_new"}, headers=alice.headers).json()["username"] == "alice_new"


def test_auth_events_are_written_to_the_audit_log(client, alice):
    client.post(f"{API}/auth/login", json={"identifier": "alice", "password": "wrong"})
    with SessionLocal() as db:
        actions = {a.action for a in db.query(AuditLog).all()}
    assert {"user.register", "auth.login", "auth.login_failed"} <= actions


def test_login_endpoint_is_rate_limited(client, alice):
    from app.middleware.rate_limit import limiter
    limiter.reset()  # the alice fixture already used two requests from the same client
    limit = get_settings().auth_rate_limit_per_minute
    codes = [client.post(f"{API}/auth/login", json={"identifier": "alice", "password": "wrong"}).status_code for _ in range(limit + 2)]
    assert codes[:limit] == [401] * limit
    assert codes[limit] == 429
    r = client.post(f"{API}/auth/login", json={"identifier": "alice", "password": "wrong"})
    assert r.json()["error"]["code"] == "RATE_LIMITED" and r.headers["retry-after"]
