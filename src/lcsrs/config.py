"""Application configuration.

Paths and settings are resolved from environment variables first, then a TOML
config file at ``~/.lcsrs/config.toml``, then sane defaults. All secret material
(the LeetCode session cookie) is read from the environment and never hardcoded.
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "lcsrs"
DEFAULT_CONFIG_DIR = Path.home() / ".lcsrs"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.toml"
DEFAULT_DB_FILE = DEFAULT_CONFIG_DIR / "lcsrs.db"

# LeetCode's public submission-list endpoint. Cookie-authenticated.
LEETCODE_BASE_URL = "https://leetcode.com"
LEETCODE_SUBMISSIONS_URL = "https://leetcode.com/api/submissions/"
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
KEYRING_SERVICE = "lcsrs"
KEYRING_USERNAME = "leetcode_session"


def _get_config_dir() -> Path:
    """Resolve the config directory, honouring LCSRS_CONFIG_DIR if set."""
    override = os.environ.get("LCSRS_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return DEFAULT_CONFIG_DIR


@dataclass
class Settings:
    """Resolved, immutable application settings."""

    config_dir: Path
    db_path: Path
    leetcode_session: str | None
    throttle_minutes: int = 15
    sync_interval_minutes: int = 30
    sync_start_hour: int = 8
    sync_end_hour: int = 23
    log_file: Path | None = field(default=None)

    @property
    def session_cookie(self) -> str | None:
        return self.leetcode_session


def _read_toml(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_keyring_session() -> str | None:
    """Read the LeetCode cookie from the OS credential store when available."""
    try:
        import keyring
        from keyring.errors import KeyringError
    except ImportError:
        return None

    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except (KeyringError, RuntimeError, OSError):
        return None


def load_settings(
    *,
    config_dir: Path | None = None,
    db_path: Path | None = None,
) -> Settings:
    """Load settings with precedence: explicit args > env > config file > defaults."""
    cfg_dir = config_dir or _get_config_dir()
    cfg_file = cfg_dir / "config.toml"
    raw = _read_toml(cfg_file)

    def _get(section: str, key: str, default: object) -> object:
        section_data = raw.get(section)
        if isinstance(section_data, dict):
            return section_data.get(key, default)
        return default

    env = os.environ

    # --- paths ---
    db = (
        db_path
        or (Path(str(env["LCSRS_DB"])) if env.get("LCSRS_DB") else None)
        or (cfg_dir / "lcsrs.db")
    )

    # --- session cookie ---
    leetcode_session = (
        env.get("LEETCODE_SESSION")
        or env.get("LCSRS_SESSION")
        or get_keyring_session()
    )

    # --- numbers ---
    def _int(key: str, default: int) -> int:
        try:
            return int(str(_get("sync", key, default)))
        except ValueError:
            return default

    throttle = _int("throttle_minutes", 15)
    interval = _int("interval_minutes", 30)
    start_hour = _int("start_hour", 8)
    end_hour = _int("end_hour", 23)

    # --- log file ---
    log_file = cfg_dir / "sync.log"

    return Settings(
        config_dir=cfg_dir,
        db_path=db,
        leetcode_session=leetcode_session,
        throttle_minutes=throttle,
        sync_interval_minutes=interval,
        sync_start_hour=start_hour,
        sync_end_hour=end_hour,
        log_file=log_file,
    )


def ensure_config_dir(config_dir: Path | None = None) -> Path:
    """Create the config directory if it does not exist, returning its path."""
    cfg_dir = config_dir or _get_config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


def write_default_config(config_dir: Path | None = None) -> Path:
    """Write a template config file if one is not already present."""
    cfg_dir = ensure_config_dir(config_dir)
    cfg_file = cfg_dir / "config.toml"
    if cfg_file.exists():
        return cfg_file
    template = """\
# lcsrs configuration
[sync]
# Minimum minutes between automatic (throttled) syncs.
throttle_minutes = 15
# Interval in minutes for the scheduled cron/systemd job.
interval_minutes = 30
# Only run the scheduled sync during these local hours (inclusive).
start_hour = 8
end_hour = 23
"""
    cfg_file.write_text(template, encoding="utf-8")
    return cfg_file


def is_windows() -> bool:
    return sys.platform == "win32"
