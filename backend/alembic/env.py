"""Alembic environment. Uses the application's own settings and model metadata."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.core.config import get_settings
from app.db.session import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
DATABASE_URL = get_settings().database_url
IS_SQLITE = DATABASE_URL.startswith("sqlite")


def run_migrations_offline() -> None:
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, render_as_batch=IS_SQLITE, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # An engine handed in by a caller (the tests do this) is used as it is; otherwise one is built from the settings.
    connectable = config.attributes.get("connection")
    if connectable is None:
        engine = create_engine(DATABASE_URL, poolclass=pool.NullPool)
        with engine.connect() as connection:
            _run(connection)
    else:
        _run(connectable)


def _run(connection) -> None:
    # SQLite cannot alter most things in place, so later migrations are rendered in "batch" mode there.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=IS_SQLITE, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
