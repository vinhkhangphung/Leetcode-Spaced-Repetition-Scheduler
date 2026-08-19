"""Textual application for lcsrs."""

from __future__ import annotations

import webbrowser
from datetime import UTC, date, datetime

from sqlmodel import Session, select
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import DataTable, Footer, Header, Static

from lcsrs.core import fsrs_engine, stats_service
from lcsrs.core.db import create_engine_for, init_db
from lcsrs.core.models import DailyActivity, FSRSCard, Problem
from lcsrs.tui.widgets.heatmap import Heatmap
from lcsrs.tui.widgets.review_table import ReviewTable
from lcsrs.tui.widgets.stats_panel import StatsPanel
from lcsrs.tui.widgets.streak_panel import StreakPanel


class LcsrsApp(App[None]):
    """Main lcsrs TUI application."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #streak { height: 3; padding: 0 1; }
    #heatmap { height: 3; padding: 0 1; }
    #middle {
        height: 1fr;
        layout: horizontal;
    }
    #stats { width: 1fr; border: solid $primary; padding: 0 1; }
    #reviews {
        width: 2fr;
        border: solid $primary;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("r", "refresh", "Re-sync"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, db_path: str, sync_error: str | None = None) -> None:
        super().__init__()
        self._db_path = db_path
        self._sync_error = sync_error
        self._engine = create_engine_for(db_path)
        init_db(self._engine)

    def compose(self) -> ComposeResult:
        yield Header()
        yield StreakPanel(0, 0, id="streak")
        yield Heatmap({}, id="heatmap")
        with Horizontal(id="middle"):
            yield StatsPanel(0.0, 0.0, 0, {}, id="stats")
            yield ReviewTable([], id="reviews")
        if self._sync_error:
            yield Static(f"[bold yellow]⚠ {self._sync_error}[/bold yellow]", id="sync-warning")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        session = Session(self._engine)
        try:
            streak = stats_service.calculate_streak(session)
            solved_today = _solved_on(session, date.today())
            heatmap_data = stats_service.get_heatmap_data(session)
            retention = stats_service.calculate_retention_rate(session)
            avg_stability = stats_service.average_stability(session)
            total_cards = stats_service.total_cards(session)
            by_state = stats_service.get_cards_by_state(session)
            due_rows = _due_rows(session)
        finally:
            session.close()

        self.query_one(StreakPanel).set_data(streak, solved_today)
        self.query_one(Heatmap).set_data(heatmap_data)
        self.query_one(StatsPanel).set_data(retention, avg_stability, total_cards, by_state)
        self.query_one(ReviewTable).set_data(due_rows)

    def action_refresh(self) -> None:
        self.refresh_data()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Open the selected due problem in the default browser."""
        if not isinstance(event.data_table, ReviewTable):
            return
        slug = str(event.row_key.value)
        webbrowser.open(f"https://leetcode.com/problems/{slug}/", new=2)
        self.notify(f"Opened LeetCode problem: {slug}")


def _solved_on(session: Session, day: date) -> int:
    row = session.get(DailyActivity, day)
    return row.problems_solved if row else 0


def _due_rows(session: Session) -> list[tuple[str, str, str, str, int]]:
    cards = session.exec(select(FSRSCard)).all()
    now = datetime.now(UTC)
    due = fsrs_engine.due_cards(cards, now=now)
    rows: list[tuple[str, str, str, str, int]] = []
    for card in due:
        problem = session.get(Problem, card.problem_slug)
        title = problem.title if problem else card.problem_slug
        difficulty = problem.difficulty if problem else "-"
        overdue_days = (now - card.due).days
        rows.append((card.problem_slug, title, difficulty, card.state, overdue_days))
    return rows
