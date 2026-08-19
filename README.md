# lcsrs - LeetCode Spaced Repetition CLI

Track LeetCode submissions and turn them into FSRS-spaced-repetition reviews.
Everything is stored locally in SQLite; no application server is required.

## Features

- Authenticated submission sync through LeetCode GraphQL.
- FSRS scheduling based on submission results.
- Accurate problem difficulty and topic metadata.
- Textual TUI with streaks, activity heatmap, retention, stability, card state,
  and due-review information.
- Press `Enter` on a selected due problem to open its LeetCode page in the
  default browser.
- Idempotent sync; repeated syncs do not duplicate submissions.

## Requirements

- Python 3.11 or newer.
- A LeetCode account and its `LEETCODE_SESSION` cookie.
- Windows Credential Manager on Windows for the recommended credential setup.

## Install On Windows

Run these commands from the project directory for a user-wide installation:

```powershell
py -m pip install --user .
```

The command installs the `lcsrs` launcher under the Python user `Scripts`
directory. If `lcsrs` is not found, add that directory to your user `PATH`:

```powershell
$userScripts = Join-Path (py -m site --user-base) "Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $userScripts) {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$userScripts", "User")
}
$env:Path = "$userScripts;$env:Path"
```

Open a new PowerShell window after changing `PATH`, then verify the command:

```powershell
lcsrs --help
```

For development, use an editable virtual-environment install instead:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

If PowerShell blocks the activation script, enable locally-created scripts for
your user:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Install On macOS Or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Configure Credentials

The recommended setup stores the cookie in the operating system credential
manager. On Windows this uses Windows Credential Manager:

```powershell
lcsrs auth
```

Enter the cookie at the hidden prompt. It is not written to the repository,
configuration file, scheduled-task arguments, or shell history.

Remove the stored credential with:

```powershell
lcsrs auth --clear
```

For a temporary session-only override in PowerShell, set the environment
variable, use the CLI, and remove it afterward:

```powershell
$env:LEETCODE_SESSION = "your-cookie-value"
lcsrs sync
Remove-Item Env:LEETCODE_SESSION
```

Do not commit the cookie or paste a complete browser cookie header into source
files or chat.

## Usage

```powershell
lcsrs sync       # sync submissions and update the local review database
lcsrs stats      # show streak, retention, stability, and card statistics
lcsrs review     # list reviews that are currently due
lcsrs tui        # launch the dashboard and due-review table
lcsrs auth       # store the LeetCode cookie in the OS credential manager
```

The TUI performs a throttled sync when it starts. In the TUI:

- Press `Tab` until the due-review table is focused.
- Use the arrow keys to select a problem.
- Press `Enter` to open the problem on LeetCode.
- Press `r` to sync and refresh the dashboard.
- Press `q` to quit.

No Windows scheduled task is installed automatically. Run `lcsrs sync` when you
want to update the local database.

## Local Data

Configuration is stored at `~/.lcsrs/config.toml` and the SQLite database is
stored at `~/.lcsrs/lcsrs.db`. Environment variables take precedence over
configuration-file values.

## Development

```powershell
python -m pytest
python -m mypy src/lcsrs --exclude "src/lcsrs/tui/"
python -m ruff check src tests
```
