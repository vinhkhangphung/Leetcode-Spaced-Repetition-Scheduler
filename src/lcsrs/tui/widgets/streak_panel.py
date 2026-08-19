"""Streak panel widget showing the current streak and today's solved count."""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget


class StreakPanel(Widget):
    """Display streak and today's solved count."""

    def __init__(self, streak: int = 0, solved_today: int = 0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._streak = streak
        self._solved_today = solved_today

    def set_data(self, streak: int, solved_today: int) -> None:
        self._streak = streak
        self._solved_today = solved_today
        self.refresh()

    def render(self) -> Text:
        return Text(
            f"🔥 {self._streak} day streak    Solved today: {self._solved_today}"
        )
