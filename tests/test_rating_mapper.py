"""Unit tests for the rating mapper."""

from __future__ import annotations

from datetime import datetime

import pytest

from lcsrs.core.models import Problem, Submission
from lcsrs.core.rating_mapper import (
    RATING_AGAIN,
    RATING_EASY,
    RATING_GOOD,
    RATING_HARD,
    map_to_fsrs_rating,
)


def _submission(status: str = "Accepted", attempts: int = 1) -> Submission:
    return Submission(
        id=1,
        problem_slug="two-sum",
        submitted_at=datetime.now(),
        status=status,
        attempts_before_ac=attempts,
    )


PROBLEM = Problem(slug="two-sum", title="Two Sum", difficulty="Easy", tags="[]")


@pytest.mark.parametrize(
    ("status", "attempts", "expected"),
    [
        ("Accepted", 1, RATING_GOOD),
        ("Accepted", 2, RATING_HARD),
        ("Accepted", 3, RATING_AGAIN),
        ("Accepted", 5, RATING_AGAIN),
        ("WrongAnswer", 1, RATING_AGAIN),
        ("TLE", 2, RATING_AGAIN),
        ("Runtime Error", 0, RATING_AGAIN),
    ],
)
def test_map_to_fsrs_rating(status: str, attempts: int, expected: int) -> None:
    assert map_to_fsrs_rating(_submission(status, attempts), PROBLEM) == expected


def test_easy_rating_is_never_produced() -> None:
    assert map_to_fsrs_rating(_submission("Accepted", 1), PROBLEM) != RATING_EASY
