from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from zipfile import ZipFile

import requests


StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int], None]  # received, total


def download_and_install_zip(
    *,
    dest_dir: str,
    download_url: str,
    zip_path: str,
    temp_extract_dir: str,
    prefer_folder: str | None = None,
    on_status: StatusCallback | None = None,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Download a zip and overlay its contents into dest_dir."""
    if on_status:
        on_status("Downloading package...")

    r = requests.get(download_url, stream=True)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0) or 0)
    received = 0
    with open(zip_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if not chunk:
                continue
            f.write(chunk)
            received += len(chunk)
            if on_progress:
                on_progress(received, total)

    if on_status:
        on_status("Extracting package...")

    if os.path.exists(temp_extract_dir):
        shutil.rmtree(temp_extract_dir)
    os.makedirs(temp_extract_dir, exist_ok=True)

    try:
        with ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_extract_dir)

        src_root = temp_extract_dir

        # Prefer a named folder anywhere inside the zip (e.g. 'realms/')
        if prefer_folder:
            for root, dirs, _files in os.walk(temp_extract_dir):
                if prefer_folder in dirs:
                    src_root = os.path.join(root, prefer_folder)
                    break

        # Otherwise, if zip contains a single top-level dir, descend into it
        if src_root == temp_extract_dir:
            extracted_items = os.listdir(temp_extract_dir)
            if len(extracted_items) == 1:
                only = os.path.join(temp_extract_dir, extracted_items[0])
                if os.path.isdir(only):
                    src_root = only

        # Merge/overlay into dest_dir (preserves existing files not in the zip)
        for item in os.listdir(src_root):
            src_path = os.path.join(src_root, item)
            dst_path = os.path.join(dest_dir, item)

            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
    finally:
        try:
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
        except Exception:
            pass
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
        except Exception:
            pass

