"""Typer CLI entrypoint for lcsrs."""

from __future__ import annotations

import logging

import typer

from lcsrs.cli.auth_cmd import auth_cmd
from lcsrs.cli.review_cmd import review_cmd
from lcsrs.cli.setup_cmd import setup_cron_cmd
from lcsrs.cli.stats_cmd import stats_cmd
from lcsrs.cli.sync_cmd import sync_cmd
from lcsrs.cli.tui_cmd import tui_cmd

app = typer.Typer(
    name="lcsrs",
    help="LeetCode spaced-repetition CLI.",
    no_args_is_help=True,
)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """lcsrs — LeetCode spaced-repetition CLI."""
    _configure_logging(verbose)


app.command("sync")(sync_cmd)
app.command("review")(review_cmd)
app.command("stats")(stats_cmd)
app.command("tui")(tui_cmd)
app.command("setup-cron")(setup_cron_cmd)
app.command("auth")(auth_cmd)


if __name__ == "__main__":
    app()
