"""Roles are a checked reference: an account cannot be given a role that does not exist."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models import Role, User
from app.models.entities import ROLES


def test_roles_exist_after_start_up(client):
    with SessionLocal() as db:
        assert {r.name for r in db.query(Role).all()} == set(ROLES)


def test_an_unknown_role_is_rejected_by_the_database(client):
    with SessionLocal() as db:
        db.add(User(email="x@example.com", username="xavier", hashed_password="h", role="superuser"))
        with pytest.raises(IntegrityError):
            db.commit()
