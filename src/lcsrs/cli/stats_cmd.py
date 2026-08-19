"""``lcsrs stats`` — print aggregate statistics."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from sqlmodel import Session

from lcsrs.cli._common import engine_context
from lcsrs.core import stats_service

console = Console()


def stats_cmd(
    db_path: str | None = typer.Option(None, "--db", help="Override database path."),
    config_dir: str | None = typer.Option(None, "--config-dir", help="Override config directory."),
) -> None:
    """Show streak, retention, and card statistics."""
    with engine_context(db_path=db_path, config_dir=config_dir) as engine:
        session = Session(engine)
        try:
            streak = stats_service.calculate_streak(session)
            retention = stats_service.calculate_retention_rate(session)
            by_state = stats_service.get_cards_by_state(session)
            total = stats_service.total_cards(session)
            avg_stability = stats_service.average_stability(session)
        finally:
            session.close()

    table = Table(title="lcsrs statistics")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Streak (days)", str(streak))
    table.add_row("Total cards", str(total))
    table.add_row("Retention (30d)", f"{retention * 100:.1f}%")
    table.add_row("Avg stability", f"{avg_stability:.2f}")

    state_table = Table(title="Cards by state")
    state_table.add_column("State")
    state_table.add_column("Count")
    for state, count in sorted(by_state.items()):
        state_table.add_row(state, str(count))
    if not by_state:
        state_table.add_row("-", "0")

    console.print(table)
    console.print(state_table)
