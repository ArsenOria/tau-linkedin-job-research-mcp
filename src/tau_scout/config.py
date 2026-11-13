from dataclasses import dataclass, field
from pathlib import Path
import os

from .errors import ScoutError


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    apify_token: str = field(default="", repr=False)

    @classmethod
    def from_env(cls) -> "Settings":
        supplied = os.environ.get("TAU_SCOUT_DATA_DIR", "").strip()
        directory = Path(supplied).expanduser() if supplied else Path.home() / ".local/share/tau-job-scout"
        if not directory.is_absolute():
            raise ScoutError("invalid_config", "TAU_SCOUT_DATA_DIR must be an absolute directory.")
        token = os.environ.get("APIFY_TOKEN", "").strip()
        if "\n" in token or "\r" in token:
            raise ScoutError("invalid_config", "APIFY_TOKEN contains an invalid newline.")
        return cls(directory, token)
