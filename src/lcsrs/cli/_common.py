"""Shared helpers for CLI commands."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine

from lcsrs.config import Settings, load_settings
from lcsrs.core import db


def get_settings(*, db_path: str | None = None, config_dir: str | None = None) -> Settings:
    return load_settings(
        config_dir=Path(config_dir) if config_dir else None,
        db_path=Path(db_path) if db_path else None,
    )


@contextmanager
def engine_context(
    *, db_path: str | None = None, config_dir: str | None = None
) -> Iterator[Engine]:
    settings = get_settings(db_path=db_path, config_dir=config_dir)
    engine = db.create_engine_for(settings.db_path)
    db.init_db(engine)
    try:
        yield engine
    finally:
        engine.dispose()
