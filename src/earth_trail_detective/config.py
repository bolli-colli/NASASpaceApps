"""Runtime settings, read from environment variables in one place.

Variables can also be written to a ``.env`` file in the project root
(see ``.env.example``). ``load_env_file`` copies them into the environment;
a variable that is already set in the shell always wins.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Repository root: <root>/src/earth_trail_detective/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CATALOG_DIR_VARIABLE = "ETD_CATALOG_DIR"
DATA_DIR_VARIABLE = "ETD_DATA_DIR"
TOKEN_VARIABLE = "EARTHDATA_TOKEN"  # Earthdata Login token for live access
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


@dataclass(frozen=True)
class Settings:
    """Where the catalog and the data cache live."""

    catalog_dir: Path
    data_dir: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build the settings; both directories can be overridden by variables."""
        return cls(
            catalog_dir=_directory(CATALOG_DIR_VARIABLE, PROJECT_ROOT / "catalog"),
            data_dir=_directory(DATA_DIR_VARIABLE, PROJECT_ROOT / "data"),
        )
