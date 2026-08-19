"""Unit tests for the canonical sync service, using a mocked API client."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from lcsrs.api.leetcode_client import RawSubmission
from lcsrs.core import sync_service
from lcsrs.core.models import DailyActivity, FSRSCard, Problem, ReviewLog, Submission, SyncState


def _raw(
    id: int, slug: str, timestamp: datetime, status: str = "Accepted", attempts: int = 1
) -> RawSubmission:
    return RawSubmission(
        id=id,
        problem_slug=slug,
        title=slug.replace("-", " ").title(),
        difficulty="Easy",
        tags=["array"],
        submitted_at=timestamp,
        status=status,
        runtime_ms=10,
        attempts_before_ac=attempts,
    )


class FakeClient:
    def __init__(self, submissions: list[RawSubmission]) -> None:
        self.submissions = submissions
        self.calls = 0

    def fetch_submissions(self, since: datetime | None) -> list[RawSubmission]:
        self.calls += 1
        if since is None:
            return self.submissions
        return [s for s in self.submissions if s.submitted_at >= since]


def _sync(engine, client, **kwargs):
    return sync_service.sync(engine, client, **kwargs)


def test_sync_inserts_problem_submission_card_and_review(engine) -> None:
    now = datetime.now(UTC)
    client = FakeClient([_raw(1, "two-sum", now - timedelta(hours=1))])
    result = _sync(engine, client, force=True, now=now)

    assert result.ok
    assert result.new_submissions == 1
    assert result.cards_updated == 1

    session = Session(engine)
    assert session.get(Problem, "two-sum") is not None
    assert session.get(Submission, 1) is not None
    assert session.get(FSRSCard, "two-sum") is not None
    assert len(session.exec(select(ReviewLog)).all()) == 1
    assert session.get(SyncState, 1).last_synced_at is not None


def test_sync_is_idempotent(engine) -> None:
    now = datetime.now(UTC)
    client = FakeClient([_raw(1, "two-sum", now - timedelta(hours=1))])

    first = _sync(engine, client, force=True, now=now)
    second = _sync(engine, client, force=True, now=now)

    assert first.new_submissions == 1
    assert second.new_submissions == 0  # no duplicates

    session = Session(engine)
    assert len(session.exec(select(Submission)).all()) == 1
    assert len(session.exec(select(ReviewLog)).all()) == 1
    assert len(session.exec(select(FSRSCard)).all()) == 1


def test_sync_skips_within_throttle(engine) -> None:
    now = datetime.now(UTC)
    client = FakeClient([_raw(1, "two-sum", now - timedelta(hours=1))])

    first = _sync(engine, client, force=True, now=now)
    assert first.new_submissions == 1

    # Second sync without force, within throttle window -> skipped.
    skipped = _sync(engine, client, force=False, throttle_minutes=15, now=now)
    assert skipped.skipped
    assert skipped.new_submissions == 0


def test_sync_force_overrides_throttle(engine) -> None:
    now = datetime.now(UTC)
    client = FakeClient([_raw(1, "two-sum", now - timedelta(hours=1))])
    _sync(engine, client, force=True, now=now)

    # With force=True, it runs again even though within throttle.
    result = _sync(engine, client, force=True, now=now)
    assert not result.skipped


def test_sync_handles_network_failure_without_raising(engine) -> None:
    class FailingClient(FakeClient):
        def fetch_submissions(self, since):
            raise RuntimeError("network down")

    client = FailingClient([])
    result = _sync(engine, client, force=True)
    assert not result.ok
    assert result.errors
    # State unchanged.
    session = Session(engine)
    assert session.get(SyncState, 1) is None


def test_sync_records_daily_activity(engine) -> None:
    now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    client = FakeClient([_raw(1, "two-sum", now - timedelta(hours=1))])
    result = _sync(engine, client, force=True, now=now)

    assert result.new_submissions == 1
    session = Session(engine)
    activity = session.get(DailyActivity, now.date())
    assert activity is not None
    assert activity.problems_solved == 1
    assert activity.reviews_done == 1
