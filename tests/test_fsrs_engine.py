"""Unit tests for the FSRS engine wrapper."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lcsrs.core import fsrs_engine
from lcsrs.core.models import FSRSCard


def _card(slug: str = "two-sum", due_days_ago: int = 0) -> FSRSCard:
    row = fsrs_engine.new_card_row(slug)
    row.due = datetime.now(UTC) - timedelta(days=due_days_ago)
    return row


def test_new_card_row_creates_learning_card() -> None:
    row = fsrs_engine.new_card_row("two-sum")
    assert row.problem_slug == "two-sum"
    assert row.state == "Learning"
    assert row.card_json  # serialized fsrs.Card


def test_review_card_advances_state_and_reps() -> None:
    row = _card()
    updated = fsrs_engine.review_card(row, 3, datetime.now(UTC))
    assert updated.reps == 1
    assert updated.last_review is not None
    assert updated.due > datetime.now(UTC)
    assert updated.card_json != row.card_json


def test_review_again_increments_lapses() -> None:
    row = _card()
    updated = fsrs_engine.review_card(row, 1, datetime.now(UTC))
    assert updated.lapses == 1


def test_review_good_does_not_lapse() -> None:
    row = _card()
    updated = fsrs_engine.review_card(row, 3, datetime.now(UTC))
    assert updated.lapses == 0


def test_due_cards_filters_and_sorts() -> None:
    overdue = _card("a", due_days_ago=5)
    due_soon = _card("b", due_days_ago=1)
    not_due = _card("c")
    not_due.due = datetime.now(UTC) + timedelta(days=1)

    due = fsrs_engine.due_cards([not_due, due_soon, overdue], now=datetime.now(UTC))
    assert [c.problem_slug for c in due] == ["a", "b"]  # sorted by oldest-due first


def test_due_cards_uses_custom_now() -> None:
    not_due = _card("a")
    now = datetime.now(UTC) - timedelta(days=10)
    due = fsrs_engine.due_cards([not_due], now=now)
    assert due == []


@pytest.mark.parametrize("rating", [1, 2, 3, 4])
def test_review_accepts_all_ratings(rating: int) -> None:
    updated = fsrs_engine.review_card(_card(), rating, datetime.now(UTC))
    assert updated.reps == 1
