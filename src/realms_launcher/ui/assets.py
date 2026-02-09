from __future__ import annotations

import os
import sys
from pathlib import Path


def app_base_dir() -> Path:
    """Base directory for resources (dev repo root or PyInstaller temp dir)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # assets.py -> ui -> realms_launcher -> src -> repo root
    return Path(__file__).resolve().parents[3]


def resource_path(relative_path: str) -> str:
    """Resolve resource path with back-compat for old asset locations."""
    base_dir = app_base_dir()

    direct = base_dir / relative_path
    if direct.exists():
        return str(direct)

    filename = os.path.basename(relative_path)
    ext = Path(filename).suffix.lower()

    if filename.lower() == "aotr_fs.ico":
        candidates = [base_dir / "assets/icons/aotr_fs.ico"]
    elif filename.lower() in ("banner.png", "background.jpg"):
        candidates = [base_dir / f"assets/images/{filename}"]
    elif filename.lower() == "icons8-one-ring-96.png":
        candidates = [base_dir / "assets/icons/icons8-one-ring-96.png"]
    elif ext in (".cur", ".ani"):
        candidates = [base_dir / f"assets/cursors/{filename}"]
    else:
        candidates = [
            base_dir / f"assets/{relative_path}",
            base_dir / f"assets/images/{filename}",
            base_dir / f"assets/icons/{filename}",
            base_dir / f"assets/cursors/{filename}",
            base_dir / f"assets/fonts/{relative_path}",
        ]

    for p in candidates:
        if p.exists():
            return str(p)

    return str(direct)

