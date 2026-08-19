"""Credential-manager commands for the LeetCode session cookie."""

from __future__ import annotations

import getpass
from contextlib import suppress

import keyring
import typer
from keyring.errors import PasswordDeleteError
from rich.console import Console

from lcsrs.config import KEYRING_SERVICE, KEYRING_USERNAME

console = Console()


def auth_cmd(
    clear: bool = typer.Option(False, "--clear", help="Remove the stored LeetCode cookie."),
) -> None:
    """Store or remove the LeetCode cookie in the OS credential manager."""
    if clear:
        with suppress(PasswordDeleteError):
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
        console.print("Removed the stored LeetCode session cookie.")
        return

    session = getpass.getpass("LeetCode session cookie (input hidden): ").strip()
    if not session:
        console.print("[bold red]A non-empty cookie is required.[/bold red]")
        raise typer.Exit(code=1)

    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, session)
    console.print("Stored the LeetCode session cookie in the OS credential manager.")
