"""Bring the database to the latest schema with Alembic, and adopt a database that was created without it.

Why this exists: in development the app can create its tables directly (AUTO_CREATE_TABLES). A database made that way has
every table but no `alembic_version` record, so a plain `alembic upgrade head` fails with "table already exists". Here such
a database is compared with the models. If it matches exactly it is marked as being at the latest revision. If it does
not match, nothing is changed and the reason is printed, because guessing could damage data.

Run it as `python -m app.db.migrate` from the backend folder. The scripts and the Docker image use it instead of calling
`alembic upgrade head` directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, pool
from sqlalchemy.engine import Connection

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.core.config import get_settings
from app.db.session import Base

BACKEND_DIR = Path(__file__).resolve().parents[2]


class UnknownSchemaError(RuntimeError):
    """The database has tables, no migration record, and a schema that differs from the models."""


def alembic_config(connection: Connection | None = None) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    if connection is not None:
        cfg.attributes["connection"] = connection
    return cfg


def bring_up_to_date(connection: Connection) -> str:
    """Upgrade (or adopt) the database behind `connection`. Returns "adopted" or "upgraded"."""
    tables = set(inspect(connection).get_table_names())
    if tables and "alembic_version" not in tables:
        drift = compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata)
        if drift:
            raise UnknownSchemaError(
                "This database has tables but no migration history, and its schema differs from the application's "
                f"({len(drift)} difference(s), first: {drift[0]!r}). Nothing was changed. For a development database, "
                "delete it and run this again. For real data, compare it with the migrations by hand."
            )
        command.stamp(alembic_config(connection), "head")
        return "adopted"
    command.upgrade(alembic_config(connection), "head")
    return "upgraded"


def main() -> int:
    engine = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    try:
        with engine.begin() as connection:
            outcome = bring_up_to_date(connection)
    except UnknownSchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print("Existing database matched the current schema and was marked as up to date." if outcome == "adopted"
          else "Database is up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
