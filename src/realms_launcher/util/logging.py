from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path


def default_log_path() -> Path:
    """Default log file path.

    Prefer `%LOCALAPPDATA%/RealmsLauncher/logs/launcher.log`, fallback to `%TEMP%`.
    """
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "RealmsLauncher" / "logs" / "launcher.log"
    return Path(tempfile.gettempdir()) / "realms_launcher" / "launcher.log"


def configure_logging(level: int = logging.INFO) -> None:
    log_path = default_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [
        logging.FileHandler(log_path, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
