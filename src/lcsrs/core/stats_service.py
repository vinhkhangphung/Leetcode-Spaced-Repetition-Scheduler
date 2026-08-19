"""Aggregation of review/streak/heatmap statistics from the database."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, select

from lcsrs.core.models import DailyActivity, FSRSCard, ReviewLog

RATING_GOOD = 3
RATING_EASY = 4


def calculate_streak(session: Session, today: date | None = None) -> int:
    """Return the number of consecutive days (ending today or yesterday) with
    any solved activity. A missing day resets the streak."""
    if today is None:
        today = date.today()

    solved_days = {
        row.day for row in session.exec(select(DailyActivity)).all() if row.problems_solved > 0
    }

    cursor = today
    if cursor not in solved_days:
        # Allow a streak to persist if today simply hasn't happened yet.
        cursor = today - timedelta(days=1)
        if cursor not in solved_days:
            return 0

    streak = 0
    while cursor in solved_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def get_heatmap_data(
    session: Session, weeks: int = 12, end: date | None = None
) -> dict[date, int]:
    """Return a mapping of date -> problems solved for the last ``weeks`` weeks."""
    if end is None:
        end = date.today()
    start = end - timedelta(weeks=weeks)
    data: dict[date, int] = {}
    for row in session.exec(select(DailyActivity)).all():
        if start <= row.day <= end:
            data[row.day] = row.problems_solved
    return data


def calculate_retention_rate(session: Session, days: int = 30) -> float:
    """Retention over the last ``days``: (Good + Easy) / total reviews."""
    since = datetime.now(UTC) - timedelta(days=days)
    ratings = [
        row.rating for row in session.exec(select(ReviewLog)).all() if row.reviewed_at >= since
    ]
    if not ratings:
        return 0.0
    good_easy = sum(1 for rating in ratings if rating in (RATING_GOOD, RATING_EASY))
    return good_easy / len(ratings)


def get_cards_by_state(session: Session) -> dict[str, int]:
    """Return counts of cards grouped by FSRS state."""
    result: dict[str, int] = defaultdict(int)
    for row in session.exec(select(FSRSCard)).all():
        result[row.state] += 1
    return dict(result)


def average_stability(session: Session) -> float:
    """Mean stability across all cards (0.0 if none)."""
    stabilities = [row.stability for row in session.exec(select(FSRSCard)).all()]
    return sum(stabilities) / len(stabilities) if stabilities else 0.0


def total_cards(session: Session) -> int:
    return len(session.exec(select(FSRSCard)).all())
