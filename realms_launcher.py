"""Compatibility entrypoint.

The launcher is now a `src/`-layout package under `src/realms_launcher/`.
This shim keeps `python realms_launcher.py` working in development.
"""

from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent
src_dir = repo_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from realms_launcher.__main__ import main  # noqa: E402  # type: ignore[import-not-found]


if __name__ == "__main__":
    main()

