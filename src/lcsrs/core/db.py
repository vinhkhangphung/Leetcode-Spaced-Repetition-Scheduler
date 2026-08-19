"""SQLite engine and session management built on SQLModel."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, create_engine

from lcsrs.core import models  # noqa: F401  (register table classes)
from lcsrs.core.models import DailyActivity, FSRSCard, Problem, ReviewLog, Submission, SyncState


def _configure_sqlite(engine: Engine) -> None:
    """Enable SQLite foreign keys and WAL for reliability."""

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def create_engine_for(db_path: Path | str) -> Engine:
    """Create a SQLAlchemy engine for the given SQLite database file."""
    path = Path(db_path)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{path}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    _configure_sqlite(engine)
    return engine


def init_db(engine: Engine) -> None:
    """Create all tables if they do not already exist."""
    SQLModel.metadata.create_all(engine)


def session_scope(engine: Engine) -> Session:
    """Return a fresh session bound to the engine."""
    return Session(engine)


def all_tables() -> list[type[SQLModel]]:
    return [Problem, Submission, FSRSCard, ReviewLog, DailyActivity, SyncState]
