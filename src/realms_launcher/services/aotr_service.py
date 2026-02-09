from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable

import requests

from ..constants import AOTR_RAR_URL
from .extract import extract_rar
from .version_service import is_lower_version


StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int], None]  # received, total


def get_aotr_version_from_lotr_str(install_path: str, *, preferred_language: str = "") -> str:
    """Parse AOTR version from `aotr/data/lotr.str`."""
    file_path = os.path.join(install_path, "aotr", "data", "lotr.str")
    if not os.path.exists(file_path):
        return "0.0.0"

    generic_pattern = r'["\']?Age of the Ring Version\s+(\d+(?:\.\d+)*)\b[^"\']*["\']?'
    ptbr_suffix_pattern = (
        r'["\']?Age of the Ring Version\s+(\d+(?:\.\d+)*)\b\s*-\s*Tradu(?:ç|c)[aã]o\s+por\s+Hans\s+Oliveira\s+\(Annatar_BR\)[^"\']*["\']?'
    )
    patterns = [ptbr_suffix_pattern, generic_pattern] if "portuguese" in (preferred_language or "").lower() else [generic_pattern]

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if re.match(r"^\s*//", line):
                    continue
                for pat in patterns:
                    m = re.search(pat, line, flags=re.IGNORECASE)
                    if m:
                        return m.group(1)
    except OSError:
        return "0.0.0"

    return "0.0.0"


def ensure_aotr(
    install_path: str,
    *,
    required_version: str,
    preferred_language: str = "",
    download_url: str = AOTR_RAR_URL,
    on_status: StatusCallback | None = None,
    on_progress: ProgressCallback | None = None,
) -> str | None:
    """Ensure AOTR meets required_version. Returns path to downloaded rar if kept."""
    current = get_aotr_version_from_lotr_str(install_path, preferred_language=preferred_language)
    if not is_lower_version(current, required_version):
        return None

    rar_path = os.path.join(install_path, "aotr.rar")
    if os.path.exists(rar_path):
        if on_status:
            on_status("Found existing AOTR RAR file. Extracting...")
        return rar_path

    if on_status:
        on_status(f"Downloading AOTR {required_version} (current: {current})...")

    r = requests.get(download_url, stream=True)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0) or 0)
    received = 0
    with open(rar_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if not chunk:
                continue
            f.write(chunk)
            received += len(chunk)
            if on_progress:
                on_progress(received, total)

    if on_status:
        on_status("Extracting AOTR...")

    realms_folder = os.path.join(install_path, "realms")
    if os.path.exists(realms_folder):
        shutil.rmtree(realms_folder)

    try:
        extract_rar(rar_path, install_path)
    except Exception:
        # Leave rar for recovery; caller decides what to do
        raise

    extracted_aotr = os.path.join(install_path, "aotr")
    if os.path.exists(extracted_aotr):
        os.rename(extracted_aotr, realms_folder)
    else:
        # no aotr folder; move everything into realms (except rar itself)
        os.makedirs(realms_folder, exist_ok=True)
        for item in os.listdir(install_path):
            item_path = os.path.join(install_path, item)
            if os.path.isfile(item_path) and item != "aotr.rar":
                shutil.move(item_path, os.path.join(realms_folder, item))
            elif os.path.isdir(item_path) and item != "realms":
                shutil.move(item_path, os.path.join(realms_folder, item))

    return rar_path

