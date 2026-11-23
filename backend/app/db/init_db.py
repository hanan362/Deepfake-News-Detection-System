"""Database initialisation helpers (used at start-up and by tests)."""
from __future__ import annotations

from app.db.session import Base, engine


def create_all() -> None:
    """Create tables directly. Production deployments should use `python -m app.db.migrate` instead."""
    import app.models  # noqa: F401  (registers the tables on Base.metadata)

    Base.metadata.create_all(bind=engine)
