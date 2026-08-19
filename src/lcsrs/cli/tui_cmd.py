"""``lcsrs tui`` — launch the Textual app, triggering a throttled sync first."""

from __future__ import annotations

import typer
from rich.console import Console

from lcsrs.api.leetcode_client import LeetCodeClient
from lcsrs.cli._common import engine_context, get_settings
from lcsrs.core import sync_service
from lcsrs.tui.app import LcsrsApp

console = Console()


def tui_cmd(
    db_path: str | None = typer.Option(None, "--db", help="Override database path."),
    config_dir: str | None = typer.Option(None, "--config-dir", help="Override config directory."),
) -> None:
    """Launch the Textual TUI. A throttled sync runs first; the TUI still
    launches on cached data if the network is unavailable."""
    settings = get_settings(db_path=db_path, config_dir=config_dir)
    sync_error: str | None = None

    with engine_context(db_path=db_path, config_dir=config_dir) as engine:
        if settings.leetcode_session:
            client = LeetCodeClient(settings.leetcode_session)
            try:
                with console.status("[bold blue]Syncing...[/bold blue]"):
                    result = sync_service.sync(
                        engine,
                        client,
                        force=False,
                        throttle_minutes=settings.throttle_minutes,
                    )
                if not result.ok:
                    sync_error = "; ".join(result.errors)
            except Exception as exc:  # noqa: BLE001 - never crash the TUI
                sync_error = str(exc)
            finally:
                client.close()
        else:
            sync_error = "No LEETCODE_SESSION set; using cached data."

    app = LcsrsApp(db_path=str(settings.db_path), sync_error=sync_error)
    app.run()
