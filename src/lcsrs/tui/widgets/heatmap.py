"""Heatmap widget rendering a GitHub-style contribution grid."""

from __future__ import annotations

from datetime import date, timedelta

from rich.text import Text
from textual.widget import Widget

# Color per intensity bucket (0 = gray, 1-2 light, 3-5 medium, 6+ dark).
_BUCKETS: list[tuple[int, str]] = [
    (0, "grey23"),
    (2, "green3"),
    (5, "green"),
    (1 << 30, "dark_green"),
]


def _color_for(count: int) -> str:
    for upper, color in _BUCKETS:
        if count <= upper:
            return color
    return "dark_green"


class Heatmap(Widget):
    """Render a row of colored blocks, one per day for the last ``weeks``."""

    def __init__(
        self, data: dict[date, int] | None = None, weeks: int = 12, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)
        self._data = data or {}
        self._weeks = weeks

    def set_data(self, data: dict[date, int]) -> None:
        self._data = data
        self.refresh()

    def render(self) -> Text:
        end = date.today()
        start = end - timedelta(weeks=self._weeks)
        cells: list[Text] = []
        cursor = start
        while cursor <= end:
            count = self._data.get(cursor, 0)
            color = _color_for(count)
            cells.append(Text("  ", style=f"on {color}"))
            cursor += timedelta(days=1)
        return Text("").join(cells)
