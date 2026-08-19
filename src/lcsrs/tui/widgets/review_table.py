"""Due-review table widget."""

from __future__ import annotations

from textual.widgets import DataTable


class ReviewTable(DataTable):
    """Show due reviews with title, difficulty, and days overdue."""

    def __init__(
        self, rows: list[tuple[str, str, str, str, int]] | None = None, **kwargs: object
    ) -> None:
        kwargs.setdefault("cursor_type", "row")
        super().__init__(**kwargs)
        self._rows = rows or []

    def on_mount(self) -> None:
        self.add_columns("Problem", "Difficulty", "State", "Days overdue")
        self._populate()

    def _populate(self) -> None:
        self.clear()
        for slug, title, difficulty, state, overdue in self._rows:
            self.add_row(title, difficulty, state, str(overdue), key=slug)

    def set_data(self, rows: list[tuple[str, str, str, str, int]]) -> None:
        self._rows = rows
        self._populate()
