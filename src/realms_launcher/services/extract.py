from __future__ import annotations

import os
from zipfile import ZipFile

from .install_service import robust_rmtree


def extract_zip(zip_path: str, dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    with ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)


def recreate_dir(path: str) -> None:
    robust_rmtree(path)
    os.makedirs(path, exist_ok=True)

