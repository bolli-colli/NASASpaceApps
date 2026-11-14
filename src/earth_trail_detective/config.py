"""Runtime settings, read from environment variables in one place.

Variables can also be written to a ``.env`` file in the project root
(see ``.env.example``). ``load_env_file`` copies them into the environment;
a variable that is already set in the shell always wins.
"""

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# Repository root: <root>/src/earth_trail_detective/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CATALOG_DIR_VARIABLE = "ETD_CATALOG_DIR"
DATA_DIR_VARIABLE = "ETD_DATA_DIR"
TOKEN_VARIABLE = "EARTHDATA_TOKEN"  # Earthdata Login token for live access
FETCH_VARIABLE = "ETD_FETCH"  # may the app fetch missing data itself? (FetchPolicy)
ENV_FILE = PROJECT_ROOT / ".env"  # optional, ignored by git


def _parse_env_line(line: str) -> tuple[str, str] | None:
    """Parse ``KEY=value`` (optionally ``export KEY="value"``); skip blanks and comments."""
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.removeprefix("export ").strip()
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    elif " #" in value:  # inline comment after an unquoted value
        value = value.split(" #", 1)[0].rstrip()
    return (key, value) if key else None


def load_env_file(path: Path = ENV_FILE) -> None:
    """Copy the variables of a ``.env`` file into the environment.

    Missing file: nothing happens. Variables already set are never overwritten,
    and empty values are skipped so the placeholder file does nothing.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        if value and key not in os.environ:
            os.environ[key] = value


def _directory(variable: str, default: Path) -> Path:
    """Read a directory from the environment, falling back to the default."""
    value = os.environ.get(variable)
    return Path(value).expanduser().resolve() if value else default


class FetchPolicy(StrEnum):
    """Whether the app itself may fill the offline cache from NASA (``ETD_FETCH``).

    Fetching always needs ``EARTHDATA_TOKEN`` as well.
    """

    OFF = "off"  # read the cache only (default: demos, judges, public deployments)
    MISSING = "missing"  # fetch series an analysis needs but the cache lacks
    REFRESH = "refresh"  # like MISSING, plus an "update from NASA" button


def _fetch_policy() -> FetchPolicy:
    value = os.environ.get(FETCH_VARIABLE, "").strip().lower()
    if not value:
        return FetchPolicy.OFF
    try:
        return FetchPolicy(value)
    except ValueError:
        allowed = ", ".join(policy.value for policy in FetchPolicy)
        raise ValueError(
            f"{FETCH_VARIABLE}={value!r} is not valid; use one of: {allowed}."
        ) from None


@dataclass(frozen=True)
class Settings:
    """Where the catalog and the data cache live, and whether the app may fetch."""

    catalog_dir: Path
    data_dir: Path
    fetch: FetchPolicy = FetchPolicy.OFF

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build the settings from environment variables (and ``.env``)."""
        return cls(
            catalog_dir=_directory(CATALOG_DIR_VARIABLE, PROJECT_ROOT / "catalog"),
            data_dir=_directory(DATA_DIR_VARIABLE, PROJECT_ROOT / "data"),
            fetch=_fetch_policy(),
        )
