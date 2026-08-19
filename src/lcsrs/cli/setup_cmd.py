"""``lcsrs setup-cron`` — install a scheduled sync job."""

from __future__ import annotations

import shutil
import subprocess
import sys

import typer
from rich.console import Console

from lcsrs.cli._common import get_settings

console = Console()


def _lcsrs_command() -> str:
    """Return the on-disk path to the installed ``lcsrs`` console script."""
    which = shutil.which("lcsrs")
    if which:
        return which
    console.print("[bold red]Could not locate the `lcsrs` executable on PATH.[/bold red]")
    raise typer.Exit(code=1)


def _install_windows(interval_minutes: int, start_hour: int, end_hour: int) -> None:
    """Install a Windows Task Scheduler task running every N minutes."""
    cmd = _lcsrs_command()
    task_name = "lcsrs-sync"
    # schtasks /create with /sc MINUTE and /mo interval.
    args = [
        "schtasks",
        "/Create",
        "/TN",
        task_name,
        "/TR",
        f'"{cmd}" sync --quiet',
        "/SC",
        "MINUTE",
        "/MO",
        str(interval_minutes),
        "/F",
    ]
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        console.print("[bold red]schtasks not found; this host is not Windows.[/bold red]")
        raise typer.Exit(code=1) from None
    if result.returncode != 0:
        console.print(f"[bold red]Failed to install task:[/bold red] {result.stderr.strip()}")
        raise typer.Exit(code=1)
    console.print(
        f"Installed Windows task '{task_name}' every {interval_minutes} minutes "
        f"(start {start_hour}h, end {end_hour}h)."
    )


def setup_cron_cmd(
    interval_minutes: int = typer.Option(30, "--interval", help="Sync interval in minutes."),
    start_hour: int = typer.Option(8, "--start-hour", help="Earliest local hour to run."),
    end_hour: int = typer.Option(23, "--end-hour", help="Latest local hour to run."),
    db_path: str | None = typer.Option(None, "--db", help="Override database path."),
    config_dir: str | None = typer.Option(
        None, "--config-dir", help="Override config directory."
    ),
) -> None:
    """Install an OS-appropriate scheduled sync job (runs `lcsrs sync --quiet`)."""
    settings = get_settings(db_path=db_path, config_dir=config_dir)
    _ = settings  # ensure config resolves before scheduling

    if sys.platform == "win32":
        _install_windows(interval_minutes, start_hour, end_hour)
    elif sys.platform == "darwin":
        console.print("[bold red]launchd installation not yet implemented on macOS.[/bold red]")
        raise typer.Exit(code=1)
    else:
        console.print(
            "[bold red]systemd/crontab installation not yet implemented on Linux.[/bold red]"
        )
        raise typer.Exit(code=1)
