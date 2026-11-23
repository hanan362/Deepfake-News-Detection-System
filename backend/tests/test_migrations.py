"""The Alembic migrations must build exactly the schema the models describe. If a model changes without a new
migration, test_models_and_migrations_agree fails, so production databases cannot silently drift from the code."""
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401
from app.db.session import Base

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture()
def alembic_cfg():
    return Config(str(BACKEND / "alembic.ini"))


@pytest.fixture()
def fresh_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'mig.db'}")
    yield engine
    engine.dispose()


def test_upgrade_creates_every_table(alembic_cfg, fresh_engine):
    with fresh_engine.begin() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")
    tables = set(inspect(fresh_engine).get_table_names())
    assert set(Base.metadata.tables) <= tables
    assert "alembic_version" in tables


def test_models_and_migrations_agree(alembic_cfg, fresh_engine):
    with fresh_engine.begin() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")
        drift = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert drift == [], f"models changed without a migration: {drift}"


def test_downgrade_removes_everything(alembic_cfg, fresh_engine):
    with fresh_engine.begin() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")
        command.downgrade(alembic_cfg, "base")
    assert set(inspect(fresh_engine).get_table_names()) <= {"alembic_version"}


def test_roles_migration_keeps_existing_accounts(alembic_cfg, fresh_engine):
    """An account created before migration 0002 keeps its role, and the roles it refers to exist afterwards."""
    from sqlalchemy import text

    with fresh_engine.begin() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "0001")
        conn.execute(text("INSERT INTO users (email, username, hashed_password, role, is_active, created_at) "
                          "VALUES ('a@example.com', 'ann', 'x', 'admin', 1, '2026-01-01 00:00:00')"))
        command.upgrade(alembic_cfg, "head")
        roles = {r[0] for r in conn.execute(text("SELECT name FROM roles"))}
        kept = conn.execute(text("SELECT role FROM users WHERE username = 'ann'")).scalar()
    assert roles == {"user", "admin"} and kept == "admin"


def test_a_database_made_without_migrations_is_adopted_not_rebuilt(fresh_engine):
    """AUTO_CREATE_TABLES builds the tables directly. The migration helper must accept that database, keep its rows and
    mark it as up to date, where a plain `alembic upgrade head` fails with "table already exists"."""
    from sqlalchemy import text

    from app.db.migrate import bring_up_to_date

    Base.metadata.create_all(fresh_engine)
    with fresh_engine.begin() as conn:
        conn.execute(text("INSERT INTO roles (name, description) VALUES ('keepme', 'kept')"))
    with fresh_engine.begin() as conn:
        assert bring_up_to_date(conn) == "adopted"
    with fresh_engine.begin() as conn:
        assert conn.execute(text("SELECT description FROM roles WHERE name = 'keepme'")).scalar_one() == "kept"
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert bring_up_to_date(conn) == "upgraded"  # now it has a history, so this is the normal path


def test_a_database_that_differs_from_the_models_is_left_alone(fresh_engine):
    from sqlalchemy import text

    from app.db.migrate import UnknownSchemaError, bring_up_to_date

    Base.metadata.create_all(fresh_engine)
    with fresh_engine.begin() as conn:
        conn.execute(text("DROP TABLE user_feedback"))
    with fresh_engine.begin() as conn:
        with pytest.raises(UnknownSchemaError):
            bring_up_to_date(conn)
    assert "alembic_version" not in set(inspect(fresh_engine).get_table_names())


def test_an_empty_database_is_migrated_normally(fresh_engine):
    from app.db.migrate import bring_up_to_date

    with fresh_engine.begin() as conn:
        assert bring_up_to_date(conn) == "upgraded"
    assert set(Base.metadata.tables) <= set(inspect(fresh_engine).get_table_names())


# --- The same checks on a real PostgreSQL server ------------------------------------------------------------------
# Skipped unless TEST_DATABASE_URL points at a PostgreSQL server. Each test gets a database of its own, created and
# dropped here, so nothing else on the server is touched. See docs/technical_documentation/testing_report.md.
import os  # noqa: E402
import uuid  # noqa: E402

from sqlalchemy.engine import make_url  # noqa: E402

_PG_URL = os.environ.get("TEST_DATABASE_URL", "")
needs_postgres = pytest.mark.skipif(not _PG_URL.startswith("postgresql"), reason="TEST_DATABASE_URL is not a PostgreSQL URL")


@pytest.fixture()
def pg_engine():
    base = make_url(_PG_URL)
    name = f"dfnd_mig_{uuid.uuid4().hex[:10]}"
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.exec_driver_sql(f'CREATE DATABASE "{name}"')
    engine = create_engine(base.set(database=name))
    yield engine
    engine.dispose()
    with admin.connect() as c:
        c.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    admin.dispose()


@needs_postgres
def test_postgres_the_application_really_uses_postgresql():
    from app.db.session import engine

    assert engine.dialect.name == "postgresql"


@needs_postgres
def test_postgres_upgrade_has_no_drift_and_downgrade_is_clean(alembic_cfg, pg_engine):
    with pg_engine.begin() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")
        drift = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert set(Base.metadata.tables) <= set(inspect(pg_engine).get_table_names())
    assert drift == [], f"models and PostgreSQL migrations disagree: {drift}"
    with pg_engine.begin() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.downgrade(alembic_cfg, "base")
    assert set(inspect(pg_engine).get_table_names()) <= {"alembic_version"}


@needs_postgres
def test_postgres_adopts_a_database_made_without_migrations(pg_engine):
    from sqlalchemy import text

    from app.db.migrate import bring_up_to_date

    Base.metadata.create_all(pg_engine)
    with pg_engine.begin() as conn:
        conn.execute(text("INSERT INTO roles (name, description) VALUES ('keepme', 'kept')"))
    with pg_engine.begin() as conn:
        assert bring_up_to_date(conn) == "adopted"
    with pg_engine.begin() as conn:
        assert conn.execute(text("SELECT description FROM roles WHERE name = 'keepme'")).scalar_one() == "kept"
