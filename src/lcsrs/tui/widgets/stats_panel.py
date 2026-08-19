"""Stats panel widget showing retention, stability, and card counts."""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget


class StatsPanel(Widget):
    """Display aggregate statistics."""

    def __init__(
        self,
        retention: float = 0.0,
        avg_stability: float = 0.0,
        total_cards: int = 0,
        by_state: dict[str, int] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._retention = retention
        self._avg_stability = avg_stability
        self._total_cards = total_cards
        self._by_state = by_state or {}

    def set_data(
        self,
        retention: float,
        avg_stability: float,
        total_cards: int,
        by_state: dict[str, int],
    ) -> None:
        self._retention = retention
        self._avg_stability = avg_stability
        self._total_cards = total_cards
        self._by_state = by_state
        self.refresh()

    def render(self) -> Text:
        parts = [
            f"Retention: {self._retention * 100:.1f}%",
            f"Avg stability: {self._avg_stability:.2f}",
            f"Total cards: {self._total_cards}",
        ]
        if self._by_state:
            state_summary = ", ".join(
                f"{state}: {count}" for state, count in sorted(self._by_state.items())
            )
            parts.append(state_summary)
        return Text("    ".join(parts))
