"""Thin wrapper around the ``fsrs`` library.

Converts between SQLModel ``FSRSCard`` rows and the library's native ``Card``
objects, and exposes the scheduling operations used by the sync service. All
interaction with ``fsrs`` internals is confined to this module.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from fsrs import Card as FSRSNativeCard
from fsrs import Rating as FSRSPRating
from fsrs import Scheduler, State

from lcsrs.core.models import FSRSCard

# Map FSRS State enum values to our storage strings.
_STATE_NAMES: dict[int, str] = {
    int(State.Learning): "Learning",
    int(State.Review): "Review",
    int(State.Relearning): "Relearning",
}

# Map our storage strings back to FSRS State enums.
_STATE_VALUES: dict[str, State] = {
    "Learning": State.Learning,
    "Review": State.Review,
    "Relearning": State.Relearning,
}

_RATING_MAP: dict[int, FSRSPRating] = {
    1: FSRSPRating.Again,
    2: FSRSPRating.Hard,
    3: FSRSPRating.Good,
    4: FSRSPRating.Easy,
}


def new_scheduler() -> Scheduler:
    """Create a default FSRS scheduler."""
    return Scheduler()


def _card_from_row(row: FSRSCard) -> FSRSNativeCard:
    return FSRSNativeCard.from_json(row.card_json)


def _row_from_card(slug: str, card: FSRSNativeCard) -> FSRSCard:
    state_name = _STATE_NAMES.get(int(card.state), "Learning")
    return FSRSCard(
        problem_slug=slug,
        card_json=card.to_json(),
        due=card.due,
        stability=card.stability if card.stability is not None else 0.0,
        difficulty=card.difficulty if card.difficulty is not None else 0.0,
        state=state_name,
        last_review=card.last_review,
    )


def new_card_row(slug: str) -> FSRSCard:
    """Create a fresh FSRSCard row for a brand-new problem."""
    return _row_from_card(slug, FSRSNativeCard())


def review_card(row: FSRSCard, rating: int, review_time: datetime) -> FSRSCard:
    """Apply an FSRS review to a card row, returning the updated row."""
    scheduler = new_scheduler()
    native = _card_from_row(row)
    updated, _review_log = scheduler.review_card(
        native, _RATING_MAP[rating], review_datetime=review_time
    )
    next_row = _row_from_card(row.problem_slug, updated)
    next_row.reps = row.reps + 1
    next_row.lapses = row.lapses + (1 if rating == 1 else 0)
    return next_row


def due_cards(rows: Sequence[FSRSCard], now: datetime | None = None) -> list[FSRSCard]:
    """Filter cards due at ``now`` (defaults to UTC now), sorted by overdue-ness."""
    if now is None:
        now = datetime.now(UTC)
    due = [row for row in rows if row.due <= now]
    due.sort(key=lambda r: r.due)
    return due
