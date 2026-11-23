"""Shared fixtures. Environment variables are set BEFORE the application is imported so that tests use a throw-away
database and storage folder and never touch the developer's real data or .env settings."""
import os
import tempfile
from types import SimpleNamespace

_TMP = tempfile.mkdtemp(prefix="ddn-test-")
# TEST_DATABASE_URL lets the same suite run against a real PostgreSQL server (see docs). The default is a throw-away
# SQLite file.
os.environ.update(
    DATABASE_URL=os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_TMP}/test.db",
    STORAGE_DIR=f"{_TMP}/storage",
    ENVIRONMENT="test",
    SECRET_KEY="test-only-secret-key-0123456789-abcdefghijklmnop",
    BCRYPT_ROUNDS="4",
    EXPOSE_RESET_TOKEN="true",
    ADMIN_EMAIL="",
    CORROBORATION_ENABLED="false",  # tests never reach the internet; the check is tested with stand-in providers
    TEXT_MATCH_ENABLED="false",  # loads the inference model; switched on in the tests of that check
    ADMIN_PASSWORD="",
)

import io  # noqa: E402
import shutil  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.middleware.rate_limit import limiter  # noqa: E402
from app.models import User  # noqa: E402

API = "/api/v1"

ARTICLE = (
    "The city council voted on Tuesday evening to approve a new budget that increases funding for public transport, "
    "road repairs and local libraries over the next two years. Council members from both parties said the plan "
    "followed months of public hearings and reviews by independent auditors. The mayor told reporters that the "
    "measure would be paid for through a modest increase in parking fees and savings from delayed administrative "
    "projects. Opposition members argued that the schedule was too ambitious and asked for quarterly progress reports."
)


@pytest.fixture(autouse=True)
def fresh_state():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    limiter.reset()
    shutil.rmtree(Path(os.environ["STORAGE_DIR"]), ignore_errors=True)  # no files leak between tests
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_user(client):
    def _make(name: str = "alice", password: str = "Passw0rd1", admin: bool = False) -> SimpleNamespace:
        r = client.post(f"{API}/auth/register", json={"email": f"{name}@example.com", "username": name, "password": password})
        assert r.status_code == 201, r.text
        uid = r.json()["id"]
        if admin:
            with SessionLocal() as db:
                db.get(User, uid).role = "admin"
                db.commit()
        login = client.post(f"{API}/auth/login", json={"identifier": name, "password": password})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        return SimpleNamespace(id=uid, name=name, email=f"{name}@example.com", password=password, token=token,
                               headers={"Authorization": f"Bearer {token}"})
    return _make


@pytest.fixture
def alice(make_user):
    return make_user("alice")


@pytest.fixture
def bob(make_user):
    return make_user("bob")


@pytest.fixture
def admin(make_user):
    return make_user("root", admin=True)


def make_image_bytes(kind: str = "noise", fmt: str = "JPEG", size=(160, 120)) -> bytes:
    """Small synthetic test images: 'noise' (random pixels) or 'flat' (one colour)."""
    if kind == "noise":
        img = Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3))
    else:
        img = Image.new("RGB", size, (120, 140, 160))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()
