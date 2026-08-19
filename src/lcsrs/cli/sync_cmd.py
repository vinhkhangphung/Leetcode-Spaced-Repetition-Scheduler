"""``lcsrs sync`` — force an on-demand sync."""

from __future__ import annotations

import logging

import typer
from rich.console import Console

from lcsrs.api.leetcode_client import LeetCodeClient
from lcsrs.cli._common import engine_context, get_settings
from lcsrs.core import sync_service

logger = logging.getLogger(__name__)
console = Console()


def sync_cmd(
    force: bool = typer.Option(
        True, "--force/--no-force", help="Force a sync regardless of throttle."
    ),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress output (for scheduled jobs)."),
    db_path: str | None = typer.Option(None, "--db", help="Override database path."),
    config_dir: str | None = typer.Option(None, "--config-dir", help="Override config directory."),
) -> None:
    """Sync LeetCode submissions into the local database."""
    settings = get_settings(db_path=db_path, config_dir=config_dir)
    if not settings.leetcode_session:
        console.print("[bold red]No LEETCODE_SESSION cookie set.[/bold red]")
        console.print("Export it first, e.g. `export LEETCODE_SESSION=...`")
        raise typer.Exit(code=1)

    with engine_context(db_path=db_path, config_dir=config_dir) as engine:
        client = LeetCodeClient(settings.leetcode_session)
        try:
            result = sync_service.sync(
                engine,
                client,
                force=force,
                throttle_minutes=settings.throttle_minutes,
            )
        finally:
            client.close()

    if result.skipped:
        if not quiet:
            console.print("Skipped: within throttle window. Use --force to override.")
        return
    if not quiet:
        if result.ok:
            console.print(
                f"Synced: {result.new_submissions} new submissions, "
                f"{result.cards_updated} cards updated."
            )
        else:
            console.print(f"[bold yellow]Sync completed with errors: {result.errors}[/bold yellow]")
            raise typer.Exit(code=1)
