"""``lcsrs review`` — non-TUI quick list of due reviews."""

from __future__ import annotations

from datetime import UTC, datetime

import typer
from rich.console import Console
from rich.table import Table
from sqlmodel import Session, select

from lcsrs.cli._common import engine_context
from lcsrs.core import fsrs_engine
from lcsrs.core.models import FSRSCard, Problem

console = Console()


def review_cmd(
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of due reviews to show."),
    db_path: str | None = typer.Option(None, "--db", help="Override database path."),
    config_dir: str | None = typer.Option(None, "--config-dir", help="Override config directory."),
) -> None:
    """List reviews that are currently due."""
    with engine_context(db_path=db_path, config_dir=config_dir) as engine:
        session = Session(engine)
        try:
            rows = session.exec(select(FSRSCard)).all()
            now = datetime.now(UTC)
            due = fsrs_engine.due_cards(rows, now=now)[:limit]

            if not due:
                console.print("No reviews due. Great job!")
                return

            table = Table(title=f"Due reviews ({len(due)})")
            table.add_column("Problem")
            table.add_column("Difficulty")
            table.add_column("State")
            table.add_column("Days overdue")

            for card in due:
                problem = session.get(Problem, card.problem_slug)
                title = problem.title if problem else card.problem_slug
                overdue_days = (now - card.due).days
                table.add_row(
                    title,
                    problem.difficulty if problem else "-",
                    card.state,
                    str(overdue_days),
                )
            console.print(table)
        finally:
            session.close()
