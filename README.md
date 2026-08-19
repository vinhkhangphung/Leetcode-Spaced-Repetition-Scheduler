# lcsrs — LeetCode Spaced Repetition CLI

Track your LeetCode submissions and convert them into FSRS-spaced-repetition
reviews, all locally. No server, no backend — SQLite is the single source of
truth.

## Features

- **Automatic sync** of LeetCode submissions (cookie-authenticated).
- **FSRS scheduling** via the `fsrs` library (no reimplementation of the math).
- **Three independent sync triggers**, all calling one canonical
  `sync_service.sync()`: on-demand, scheduled (cron/systemd/Task Scheduler),
  and on TUI launch (throttled).
- **Textual TUI** with a contribution heatmap, streak counter, due-review table
  and stats panel.
- **Idempotent** — running `sync` repeatedly never duplicates data.

## Install

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the activation command in the same PowerShell window where you will run
`lcsrs`. If PowerShell blocks the activation script, enable locally-created
scripts for your user with:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

If you do not want to activate the virtual environment, invoke the installed
launcher by its path instead:

```powershell
.\.venv\Scripts\lcsrs.exe tui
```

## Configure

Store your LeetCode session cookie in the operating system credential manager:

```powershell
lcsrs auth
```

The prompt hides the cookie while you enter it. The cookie is stored in
Windows Credential Manager under the `lcsrs` entry and is never written to the
repository, configuration file, scheduled-task command, or shell history.
Remove it when needed with:

```powershell
lcsrs auth --clear
```

For a temporary session-only override, set `LEETCODE_SESSION` in the current
PowerShell process. It takes precedence over the credential-manager entry and
is not persisted:

```bash
export LEETCODE_SESSION="your-cookie-value"
```

In PowerShell, use `$env:LEETCODE_SESSION = ...` and remove it afterward with
`Remove-Item Env:LEETCODE_SESSION`.

Configuration lives in `~/.lcsrs/config.toml` (environment variables take
precedence). The database is stored at `~/.lcsrs/lcsrs.db`.

## Usage

```bash
lcsrs sync        # force a sync now
lcsrs stats       # show streak, retention, card counts
lcsrs review      # quick (non-TUI) list of due reviews
lcsrs tui         # launch the TUI (throttled sync happens first)
lcsrs setup-cron  # install a scheduled sync job (OS-appropriate)
lcsrs auth        # store the LeetCode cookie in the OS credential manager
```

In the TUI, focus the due-review table with `Tab`, select a problem with the
arrow keys, and press `Enter` to open its LeetCode page in the default browser.
Press `r` to re-sync and refresh the dashboard, or `q` to quit.

## Development

```bash
pytest
mypy lcsrs/
ruff check src tests
```
