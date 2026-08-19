"""SQLModel table definitions.

All persistence goes through these models. FSRS card state is stored as a
JSON blob (``card_json``) — the canonical representation produced by the
``fsrs`` library — alongside denormalised columns (``due``, ``state``, ...)
that make querying fast and avoid touching library internals elsewhere.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from lcsrs.core.timezone import UTCDateTime


class Problem(SQLModel, table=True):
    """A LeetCode problem, keyed by its URL slug."""

    slug: str = Field(primary_key=True)
    title: str
    difficulty: str  # Easy | Medium | Hard
    tags: str  # JSON-encoded list of tag strings

    def tag_list(self) -> list[str]:
        import json

        try:
            value = json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return []
        return value if isinstance(value, list) else []


class Submission(SQLModel, table=True):
    """A single LeetCode submission."""

    id: int = Field(primary_key=True)  # LeetCode submission id
    problem_slug: str = Field(foreign_key="problem.slug", index=True)
    submitted_at: datetime = Field(sa_column=Column("submitted_at", UTCDateTime, index=True))
    status: str  # Accepted | WrongAnswer | TLE | ...
    runtime_ms: int | None = None
    attempts_before_ac: int = 0
    time_spent_sec: int | None = None  # reserved; not used by the heuristic


class FSRSCard(SQLModel, table=True):
    """Spaced-repetition state for a single problem."""

    problem_slug: str = Field(primary_key=True, foreign_key="problem.slug")
    card_json: str  # canonical fsrs.Card serialization
    due: datetime = Field(sa_column=Column("due", UTCDateTime, index=True))
    stability: float = 0.0
    difficulty: float = 0.0
    state: str  # New | Learning | Review | Relearning
    last_review: datetime | None = Field(sa_column=Column("last_review", UTCDateTime))
    reps: int = 0
    lapses: int = 0


class ReviewLog(SQLModel, table=True):
    """A record of a FSRS review of a problem."""

    __table_args__ = (
        UniqueConstraint("problem_slug", "reviewed_at", "rating", name="uq_review"),
    )

    id: int | None = Field(default=None, primary_key=True)
    problem_slug: str = Field(foreign_key="problem.slug", index=True)
    reviewed_at: datetime = Field(sa_column=Column("reviewed_at", UTCDateTime, index=True))
    rating: int  # 1-4 per FSRS (Again=1 ... Easy=4)


class DailyActivity(SQLModel, table=True):
    """Aggregated per-day counters used by the heatmap and streak."""

    day: date = Field(primary_key=True)
    problems_solved: int = 0
    reviews_done: int = 0


class SyncState(SQLModel, table=True):
    """Singleton row tracking the last successful sync timestamp."""

    id: int = Field(default=1, primary_key=True)
    last_synced_at: datetime | None = Field(sa_column=Column("last_synced_at", UTCDateTime))
