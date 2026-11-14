"""Runtime settings, read from environment variables in one place."""

import os
from dataclasses import dataclass
from pathlib import Path

# Repository root: <root>/src/earth_trail_detective/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CATALOG_DIR_VARIABLE = "ETD_CATALOG_DIR"
DATA_DIR_VARIABLE = "ETD_DATA_DIR"
TOKEN_VARIABLE = "EARTHDATA_TOKEN"  # Earthdata Login token for live access


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
