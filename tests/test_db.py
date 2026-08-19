"""Unit tests for the database engine creation."""

from __future__ import annotations

from pathlib import Path

from lcsrs.core import db


def test_create_engine_for_creates_parent_directory(tmp_path) -> None:
    db_path = tmp_path / "nested" / "dir" / "lcsrs.db"
    engine = db.create_engine_for(db_path)
    try:
        assert db_path.parent.exists()
        db.init_db(engine)
        assert db_path.exists()
    finally:
        engine.dispose()


def test_create_engine_for_existing_directory(tmp_path) -> None:
    db_path = tmp_path / "lcsrs.db"
    engine = db.create_engine_for(db_path)
    try:
        db.init_db(engine)
        assert db_path.exists()
    finally:
        engine.dispose()
