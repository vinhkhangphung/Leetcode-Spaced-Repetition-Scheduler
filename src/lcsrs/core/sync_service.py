"""The single canonical sync routine.

Every sync trigger (CLI ``sync``, scheduled cron/systemd/Task Scheduler job,
and TUI launch) calls :func:`sync` here. There is no duplicated sync logic
elsewhere in the codebase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session

from lcsrs.api.leetcode_client import LeetCodeClient, RawSubmission
from lcsrs.core import fsrs_engine
from lcsrs.core.models import (
    DailyActivity,
    FSRSCard,
    Problem,
    ReviewLog,
    Submission,
    SyncState,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Outcome of a sync run."""

    skipped: bool = False
    new_submissions: int = 0
    cards_updated: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _get_last_sync(session: Session) -> datetime | None:
    row = session.get(SyncState, 1)
    if row is None:
        # Stage the singleton row without committing; it will be committed or
        # rolled back as part of the surrounding transaction.
        session.add(SyncState(id=1))
        return None
    return row.last_synced_at


def _set_last_sync(session: Session, when: datetime) -> None:
    row = session.get(SyncState, 1)
    if row is None:
        row = SyncState(id=1)
        session.add(row)
    row.last_synced_at = when


def _upsert_problem(session: Session, raw: RawSubmission) -> None:
    existing = session.get(Problem, raw.problem_slug)
    if existing is None:
        session.add(
            Problem(
                slug=raw.problem_slug,
                title=raw.title,
                difficulty=raw.difficulty,
                tags=_json_dumps(raw.tags),
            )
        )
    else:
        # Refresh metadata that may have changed, but never overwrite tags with
        # an empty list (some endpoint responses omit tags).
        if raw.tags:
            existing.tags = _json_dumps(raw.tags)
        if raw.title:
            existing.title = raw.title
        if raw.difficulty:
            existing.difficulty = raw.difficulty


def _json_dumps(value: list[str]) -> str:
    import json

    return json.dumps(value)


def _insert_submission(session: Session, raw: RawSubmission) -> bool:
    """Insert a submission if it is not already present. Returns True if new."""
    existing = session.get(Submission, raw.id)
    if existing is not None:
        return False
    session.add(
        Submission(
            id=raw.id,
            problem_slug=raw.problem_slug,
            submitted_at=raw.submitted_at,
            status=raw.status,
            runtime_ms=raw.runtime_ms,
            attempts_before_ac=raw.attempts_before_ac,
        )
    )
    return True


def _bump_daily_solved(session: Session, day: date) -> None:
    row = session.get(DailyActivity, day)
    if row is None:
        session.add(DailyActivity(day=day, problems_solved=1, reviews_done=0))
    else:
        row.problems_solved += 1


def _bump_daily_reviews(session: Session, day: date) -> None:
    row = session.get(DailyActivity, day)
    if row is None:
        session.add(DailyActivity(day=day, problems_solved=0, reviews_done=1))
    else:
        row.reviews_done += 1


def _process_submission(session: Session, raw: RawSubmission) -> bool:
    """Upsert problem + submission and apply an FSRS review.

    Returns True if the submission was newly inserted (and thus counts toward
    the sync totals).
    """
    _upsert_problem(session, raw)
    is_new = _insert_submission(session, raw)
    if not is_new:
        return False

    problem = session.get(Problem, raw.problem_slug)
    assert problem is not None

    from lcsrs.core.rating_mapper import map_to_fsrs_rating

    card = session.get(FSRSCard, raw.problem_slug)
    if card is None:
        card = fsrs_engine.new_card_row(raw.problem_slug)
        session.add(card)

    rating = map_to_fsrs_rating(submission=raw_to_submission(raw), problem=problem)
    updated = fsrs_engine.review_card(card, rating, raw.submitted_at)
    # Copy back onto the attached instance so SQLAlchemy persists the change.
    _apply_card_update(card, updated)

    session.add(
        ReviewLog(
            problem_slug=raw.problem_slug,
            reviewed_at=raw.submitted_at,
            rating=rating,
        )
    )
    _bump_daily_solved(session, raw.submitted_at.date())
    _bump_daily_reviews(session, raw.submitted_at.date())
    return True


def raw_to_submission(raw: RawSubmission) -> Submission:
    """Build a transient Submission for use by the pure rating mapper."""
    return Submission(
        id=raw.id,
        problem_slug=raw.problem_slug,
        submitted_at=raw.submitted_at,
        status=raw.status,
        runtime_ms=raw.runtime_ms,
        attempts_before_ac=raw.attempts_before_ac,
    )


def _apply_card_update(target: FSRSCard, updated: FSRSCard) -> None:
    target.card_json = updated.card_json
    target.due = updated.due
    target.stability = updated.stability
    target.difficulty = updated.difficulty
    target.state = updated.state
    target.last_review = updated.last_review
    target.reps = updated.reps
    target.lapses = updated.lapses


def sync(
    engine: Engine,
    client: LeetCodeClient,
    *,
    force: bool = False,
    throttle_minutes: int = 15,
    now: datetime | None = None,
) -> SyncResult:
    """Run a single sync.

    - Reads the last-synced timestamp from ``SyncState``.
    - If not ``force`` and the throttle window hasn't elapsed, skips.
    - Fetches new submissions, upserts problems, dedupes submissions, applies
      FSRS reviews, updates daily counters and the sync timestamp.
    - Wrapped in a single transaction that rolls back on error.
    - Never raises on network failure; returns a ``SyncResult`` with errors.
    """
    if now is None:
        now = datetime.now(UTC)

    result = SyncResult()
    session = Session(engine)

    try:
        last_sync = _get_last_sync(session)
        if not force and last_sync is not None:
            elapsed = (now - last_sync).total_seconds() / 60.0
            if elapsed < throttle_minutes:
                result.skipped = True
                return result

        try:
            raw_submissions = client.fetch_submissions(last_sync if last_sync else _epoch())
        except Exception as exc:  # noqa: BLE001 - network/api errors must not crash
            logger.exception("Sync fetch failed")
            result.errors.append(str(exc))
            session.rollback()
            return result

        # Begin the transactional write phase.
        try:
            for raw in raw_submissions:
                if _process_submission(session, raw):
                    result.new_submissions += 1
                    result.cards_updated += 1
            _set_last_sync(session, now)
            session.commit()
        except (IntegrityError, SQLAlchemyError) as exc:
            logger.exception("Sync transaction failed; rolling back")
            session.rollback()
            result.errors.append(str(exc))
    finally:
        session.close()

    return result


def _epoch() -> datetime:
    return datetime.fromtimestamp(0, tz=UTC)
