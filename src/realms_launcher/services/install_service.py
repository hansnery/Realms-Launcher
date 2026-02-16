from __future__ import annotations

import os
import stat
import shutil
from collections.abc import Callable
from zipfile import ZipFile

import requests


StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int], None]  # received, total


def _remove_readonly(func, path, _exc_info):
    """Error handler for shutil.rmtree: clear read-only flag and retry."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def robust_rmtree(path: str) -> None:
    """Remove a directory tree, handling read-only files on Windows."""
    if os.path.exists(path):
        shutil.rmtree(path, onerror=_remove_readonly)


def _copy2_force(src: str, dst: str, **kwargs) -> str:
    """Copy src to dst, clearing read-only flag on destination if needed."""
    if os.path.exists(dst):
        try:
            os.chmod(dst, stat.S_IWRITE)
        except OSError:
            pass
    return shutil.copy2(src, dst, **kwargs)


def robust_copytree(src: str, dst: str, **kwargs) -> str:
    """Copy a directory tree, handling read-only destination files."""
    return shutil.copytree(src, dst, copy_function=_copy2_force, **kwargs)


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

    robust_rmtree(temp_extract_dir)
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
                robust_copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                _copy2_force(src_path, dst_path)
    finally:
        try:
            robust_rmtree(temp_extract_dir)
        except Exception:
            pass
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
        except Exception:
            pass

