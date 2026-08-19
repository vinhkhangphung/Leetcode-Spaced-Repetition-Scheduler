"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine

from lcsrs.core import db
from lcsrs.core.models import Problem


@pytest.fixture()
def engine(tmp_path) -> Iterator[Engine]:
    """In-memory-free SQLite engine backed by a temp file (WAL friendly)."""
    e = db.create_engine_for(tmp_path / "test.db")
    db.init_db(e)
    try:
        yield e
    finally:
        e.dispose()


@pytest.fixture()
def session(engine) -> Iterator:
    from sqlmodel import Session

    s = Session(engine)
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def sample_problem() -> Problem:
    return Problem(
        slug="two-sum", title="Two Sum", difficulty="Easy", tags='["array","hash-table"]'
    )