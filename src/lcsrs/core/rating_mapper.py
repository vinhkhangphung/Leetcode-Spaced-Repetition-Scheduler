"""Map a LeetCode submission to an FSRS rating (1-4).

Pure functions with no I/O, fully unit-testable. The heuristic uses only data
that LeetCode's submission history reliably provides (attempts before accept);
``time_spent_sec`` is intentionally excluded.
"""

from __future__ import annotations

from lcsrs.core.models import Problem, Submission

RATING_AGAIN = 1
RATING_HARD = 2
RATING_GOOD = 3
RATING_EASY = 4

# Attempts-before-accept thresholds for the heuristic.
AGAIN_ATTEMPTS = 3  # 3+ failed attempts => forget (Again)
HARD_ATTEMPTS = 2  # exactly 2 attempts => Hard


def map_to_fsrs_rating(submission: Submission, problem: Problem) -> int:
    """Return an FSRS rating (1-4) for a submission.

    Rules (documented thresholds):
    - If the submission was not Accepted, treat it as a failed attempt -> Again (1).
    - If the number of attempts before accept is 3 or more -> Again (1).
    - If the number of attempts before accept is exactly 2 -> Hard (2).
    - Otherwise (single successful attempt) -> Good (3).

    The ``Easy`` (4) rating is reserved and intentionally not produced: LeetCode
    does not provide a reliable "effortless" signal, so we avoid inflating
    intervals with unverified confidence.
    """
    if submission.status != "Accepted":
        return RATING_AGAIN

    attempts = submission.attempts_before_ac
    if attempts >= AGAIN_ATTEMPTS:
        return RATING_AGAIN
    if attempts >= HARD_ATTEMPTS:
        return RATING_HARD
    return RATING_GOOD
