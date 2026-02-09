from __future__ import annotations

import os
import shutil
from zipfile import ZipFile

import rarfile


def extract_zip(zip_path: str, dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    with ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)


def recreate_dir(path: str) -> None:
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def extract_rar(rar_path: str, dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    with rarfile.RarFile(rar_path, "r") as rf:
        rf.extractall(dest_dir)

