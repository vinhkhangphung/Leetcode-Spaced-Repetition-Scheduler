"""Unit tests for the stats service."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from lcsrs.core import stats_service
from lcsrs.core.models import DailyActivity, FSRSCard, Problem, ReviewLog


def _activity(session, day: date, solved: int = 1) -> None:
    session.add(DailyActivity(day=day, problems_solved=solved, reviews_done=0))


def _problem(session, slug: str) -> Problem:
    problem = Problem(slug=slug, title=slug, difficulty="Easy", tags="[]")
    session.add(problem)
    session.flush()  # ensure FK target exists before cards reference it
    return problem


def test_streak_counting_consecutive_days(session) -> None:
    today = date(2026, 1, 15)
    for offset in range(3):
        _activity(session, today - timedelta(days=offset))
    session.commit()
    assert stats_service.calculate_streak(session, today=today) == 3


def test_streak_resets_after_missed_day(session) -> None:
    today = date(2026, 1, 15)
    _activity(session, today)  # today
    _activity(session, today - timedelta(days=2))  # two days ago (gap)
    session.commit()
    assert stats_service.calculate_streak(session, today=today) == 1


def test_streak_allows_today_not_started(session) -> None:
    today = date(2026, 1, 15)
    _activity(session, today - timedelta(days=1))
    _activity(session, today - timedelta(days=2))
    session.commit()
    # Today has no activity yet; streak should still count yesterday's run.
    assert stats_service.calculate_streak(session, today=today) == 2


def test_streak_zero_with_no_activity(session) -> None:
    assert stats_service.calculate_streak(session, today=date(2026, 1, 15)) == 0


def test_heatmap_data_restricts_to_window(session) -> None:
    end = date(2026, 1, 15)
    inside = end - timedelta(days=5)
    outside = end - timedelta(weeks=20)
    _activity(session, inside, solved=3)
    _activity(session, outside, solved=9)
    session.commit()

    data = stats_service.get_heatmap_data(session, weeks=12, end=end)
    assert data.get(inside) == 3
    assert outside not in data


def test_retention_rate_counts_good_and_easy(session) -> None:
    _problem(session, "p")
    now = datetime.now(UTC)
    for rating in (1, 2, 3, 4):
        session.add(ReviewLog(problem_slug="p", reviewed_at=now, rating=rating))
    session.commit()
    retention = stats_service.calculate_retention_rate(session, days=30)
    # Good(3) + Easy(4) = 2 of 4 total => 0.5
    assert retention == 0.5


def test_retention_rate_zero_with_no_reviews(session) -> None:
    assert stats_service.calculate_retention_rate(session) == 0.0


def test_cards_by_state(session) -> None:
    for slug in ("a", "b", "c"):
        _problem(session, slug)
    session.add(
        FSRSCard(
            problem_slug="a",
            card_json="{}",
            due=datetime.now(UTC),
            stability=1.0,
            difficulty=1.0,
            state="Review",
        )
    )
    session.add(
        FSRSCard(
            problem_slug="b",
            card_json="{}",
            due=datetime.now(UTC),
            stability=1.0,
            difficulty=1.0,
            state="Review",
        )
    )
    session.add(
        FSRSCard(
            problem_slug="c",
            card_json="{}",
            due=datetime.now(UTC),
            stability=1.0,
            difficulty=1.0,
            state="Learning",
        )
    )
    session.commit()
    by_state = stats_service.get_cards_by_state(session)
    assert by_state == {"Review": 2, "Learning": 1}


def test_average_stability(session) -> None:
    _problem(session, "a")
    _problem(session, "b")
    session.add(
        FSRSCard(
            problem_slug="a",
            card_json="{}",
            due=datetime.now(UTC),
            stability=2.0,
            difficulty=1.0,
            state="Review",
        )
    )
    session.add(
        FSRSCard(
            problem_slug="b",
            card_json="{}",
            due=datetime.now(UTC),
            stability=4.0,
            difficulty=1.0,
            state="Review",
        )
    )
    session.commit()
    assert stats_service.average_stability(session) == 3.0
