from __future__ import annotations

# flake8: noqa

from dataclasses import dataclass
import json
import os
import shutil
from collections.abc import Callable

import requests

from ..constants import (
    BASE_MOD_VERSION,
    BASE_MOD_ZIP_URL,
    FULL_MOD_ZIP_URL,
    UPDATE_ZIP_URL,
)
from . import install_service
from .version_service import fetch_remote_version_info, is_lower_version


StatusCallback = Callable[[str, str], None]  # (message, fg_color)
ProgressCallback = Callable[[float], None]  # 0..100


@dataclass(frozen=True)
class InstallResult:
    success: bool
    installed_version: str | None = None
    error: str | None = None
    realms_folder: str | None = None


def _status(cb: StatusCallback | None, msg: str, fg: str = "blue") -> None:
    if cb:
        cb(msg, fg)


def _progress(cb: ProgressCallback | None, pct: float) -> None:
    if cb:
        try:
            cb(float(pct))
        except Exception:
            pass


def delete_specific_folders(
    install_path: str,
    *,
    on_status: StatusCallback | None = None,
) -> None:
    """Delete specific map folders from the mod installation directory."""
    realms_folder = os.path.join(install_path, "realms")
    maps_folder = os.path.join(realms_folder, "maps")

    map_folders_to_delete = [
        # Adventure maps
        "map mp alternate arthedain",
        "map mp alternate dorwinion",
        "map mp alternate durins folk",
        "map mp alternate rhun",
        "map mp alternate shadow and flame",
        # Fortress maps
        "map mp fortress abrakhan",
        "map mp fortress amon sul",
        "map mp fortress barrow of cargast",
        "map mp fortress caras galadhon",
        "map mp fortress carn dum",
        "map mp fortress dimrill gate",
        "map mp fortress dol amroth",
        "map mp fortress dol guldur",
        "map mp fortress durthang",
        "map mp fortress edennogrod",
        "map mp fortress edoras",
        "map mp fortress esgaroth",
        "map mp fortress fornost",
        "map mp fortress framsburg",
        "map mp fortress gundabad",
        "map mp fortress halls of the elvenking",
        "map mp fortress helms deep",
        "map mp fortress hidar",
        "map mp fortress hornburg",
        "map mp fortress ironfoots halls",
        "map mp fortress isengard",
        "map mp fortress kingdom of erebor",
        "map mp fortress last homely house",
        "map mp fortress minas morgul",
        "map mp fortress minas tirith",
        "map mp fortress pelargir",
        "map mp fortress the angle",
        "map mp fortress the dwarf hold",
        "map mp fortress thorins halls",
        "map mp fortress umbar",
        "map mp fortress wulfborg",
    ]

    try:
        _status(on_status, "Performing post-installation cleanup...", "blue")
        for map_folder in map_folders_to_delete:
            folder_path = os.path.join(maps_folder, map_folder)
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                _status(on_status, f"Cleaning up: Removing {map_folder}...", "blue")
                shutil.rmtree(folder_path)
        _status(on_status, "Map cleanup completed successfully.", "green")
    except Exception as e:
        _status(on_status, f"Warning: Map cleanup failed - {str(e)}", "orange")


def verify_folder_copy(source_folder: str, dest_folder: str) -> tuple[bool, str]:
    """Verify destination folder is a complete copy of the source folder."""
    try:
        if not os.path.exists(source_folder):
            return False, "Source folder does not exist"
        if not os.path.exists(dest_folder):
            return False, "Destination folder does not exist"

        source_files: list[str] = []
        dest_files: list[str] = []

        for root, _dirs, files in os.walk(source_folder):
            rel_path = os.path.relpath(root, source_folder)
            for file in files:
                source_files.append(os.path.join(rel_path, file))

        for root, _dirs, files in os.walk(dest_folder):
            rel_path = os.path.relpath(root, dest_folder)
            for file in files:
                dest_files.append(os.path.join(rel_path, file))

        if set(source_files) != set(dest_files):
            missing_files = set(source_files) - set(dest_files)
            extra_files = set(dest_files) - set(source_files)
            return False, f"File mismatch. Missing: {len(missing_files)}, Extra: {len(extra_files)}"

        sample_files = source_files[: min(50, len(source_files))]
        for file_path in sample_files:
            source_file = os.path.join(source_folder, file_path)
            dest_file = os.path.join(dest_folder, file_path)

            if not os.path.exists(dest_file):
                return False, f"Destination file missing: {file_path}"

            if os.path.getsize(source_file) != os.path.getsize(dest_file):
                return False, f"File size mismatch: {file_path}"

        return True, "Copy verification successful"
    except Exception as e:
        return False, f"Verification error: {str(e)}"


def prepare_realms_folder(
    install_path: str,
    *,
    on_status: StatusCallback | None = None,
) -> str:
    """Create a copy of the 'aotr' folder and rename it to 'realms'."""
    aotr_folder = os.path.join(install_path, "aotr")
    realms_folder = os.path.join(install_path, "realms")

    if not os.path.exists(aotr_folder):
        raise Exception("'aotr' folder not found in the installation directory")

    if os.path.exists(realms_folder):
        _status(on_status, "Verifying existing realms folder...", "blue")
        is_valid, message = verify_folder_copy(aotr_folder, realms_folder)
        if is_valid:
            _status(on_status, "Existing realms folder is valid.", "green")
            return realms_folder

        _status(on_status, f"Invalid realms folder detected: {message}. Removing...", "orange")
        shutil.rmtree(realms_folder)

    _status(on_status, "Copying AOTR folder...", "blue")
    try:
        shutil.copytree(aotr_folder, realms_folder)
    except Exception as e:
        if os.path.exists(realms_folder):
            shutil.rmtree(realms_folder)
        raise Exception(f"Failed to copy AOTR folder: {str(e)}")

    _status(on_status, "Verifying copy integrity...", "blue")
    is_valid, message = verify_folder_copy(aotr_folder, realms_folder)
    if not is_valid:
        if os.path.exists(realms_folder):
            shutil.rmtree(realms_folder)
        raise Exception(f"Copy verification failed: {message}")

    _status(on_status, "Realms folder prepared successfully.", "green")
    return realms_folder


def download_and_install_package(
    install_path: str,
    download_url: str,
    version_label: str,
    version_number: str,
    *,
    on_status: StatusCallback | None = None,
    on_progress_pct: ProgressCallback | None = None,
) -> None:
    """Download and install a specific package (realms base/update/full)."""
    if version_label == "base mod":
        _status(on_status, f"Downloading Realms in Exile version {version_number}...", "blue")
    elif version_label == "full version":
        _status(on_status, f"Downloading Realms in Exile full version {version_number}...", "blue")
    else:
        _status(on_status, f"Downloading {version_label} version {version_number}...", "blue")

    parent_dir = os.path.dirname(install_path)
    zip_path = os.path.join(parent_dir, f"{version_label.replace(' ', '_')}.zip")
    temp_dir = os.path.join(parent_dir, "temp_extraction")

    _status(on_status, f"Installing {version_label}...", "blue")

    def _on_progress(received: int, total: int):
        pct = (received / total) * 100 if total else 0.0
        _progress(on_progress_pct, pct)

    install_service.download_and_install_zip(
        dest_dir=install_path,
        download_url=download_url,
        zip_path=zip_path,
        temp_extract_dir=temp_dir,
        prefer_folder="realms",
        on_progress=_on_progress,
    )

    delete_specific_folders(install_path, on_status=on_status)
    _status(on_status, f"{version_label.capitalize()} version {version_number} installed successfully", "green")


def _read_local_version_info(version_file: str) -> tuple[str | None, str | None]:
    """Read local version and aotr_version from realms_version.json.

    Returns (version, aotr_version) — either may be None if missing.
    """
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return None, None
        data = json.loads(content) or {}
        version = data.get("version")
        aotr_version = data.get("aotr_version")
        return (str(version) if version else None, str(aotr_version) if aotr_version else None)
    except Exception:
        return None, None


def _write_local_version_info(version_file: str, version: str, aotr_version: str) -> None:
    """Write version and aotr_version to realms_version.json."""
    with open(version_file, "w", encoding="utf-8") as f:
        json.dump({"version": version, "aotr_version": aotr_version}, f)


def install_or_update_realms(
    install_path: str,
    *,
    preferred_language: str = "",
    on_status: StatusCallback | None = None,
    on_progress_pct: ProgressCallback | None = None,
) -> InstallResult:
    """Main workflow: check cloud AOTR versions, then install/update realms accordingly.

    Decision logic (both AOTR version fields come from the cloud version.json):
    - If required_aotr_version == current_aotr_version:
        Lightweight path — copy aotr/ -> realms/, download base mod + update.
    - If required_aotr_version != current_aotr_version:
        Full version path — download a complete Realms package (includes AOTR files).

    For existing installations, if the local aotr_version differs from the cloud's
    required_aotr_version, treat as a fresh install (AOTR base has changed).
    """
    try:
        install_path = os.path.normpath(install_path)
        realms_folder = os.path.join(install_path, "realms")
        version_file = os.path.join(realms_folder, "realms_version.json")

        # 1. Fetch remote version info
        _status(on_status, "Checking for updates...", "blue")
        try:
            remote_info = fetch_remote_version_info()
            remote_version = remote_info.version
            required_aotr = remote_info.required_aotr_version
            current_aotr = remote_info.current_aotr_version
        except Exception:
            return InstallResult(success=False, error="Failed to fetch version info from server.")

        # 2. Determine if AOTR versions are in sync (both from cloud)
        aotr_versions_match = (required_aotr == current_aotr)

        # 3. Read local version info
        local_version, local_aotr_version = _read_local_version_info(version_file)

        # 4. Determine install type
        is_fresh_install = local_version is None
        aotr_base_changed = (
            not is_fresh_install
            and local_aotr_version is not None
            and local_aotr_version != required_aotr
        )

        # If AOTR base changed for an existing install, treat as fresh install
        if aotr_base_changed:
            _status(
                on_status,
                f"AOTR base version changed ({local_aotr_version} -> {required_aotr}). Reinstalling...",
                "blue",
            )
            # Remove existing realms folder for a clean install
            if os.path.exists(realms_folder):
                shutil.rmtree(realms_folder)
            is_fresh_install = True

        if is_fresh_install:
            if aotr_versions_match:
                # --- Lightweight path: copy aotr -> realms, then base + update ---
                _status(on_status, "Preparing installation from AOTR folder...", "blue")
                realms_folder = prepare_realms_folder(install_path, on_status=on_status)

                # Install base mod
                _status(on_status, f"Installing base version {BASE_MOD_VERSION}...", "blue")
                download_and_install_package(
                    realms_folder,
                    BASE_MOD_ZIP_URL,
                    "base mod",
                    BASE_MOD_VERSION,
                    on_status=on_status,
                    on_progress_pct=on_progress_pct,
                )
                _write_local_version_info(version_file, BASE_MOD_VERSION, required_aotr)

                # Install update if available
                if is_lower_version(BASE_MOD_VERSION, remote_version):
                    _status(on_status, f"Base installed. Updating to version {remote_version}...", "blue")
                    try:
                        download_and_install_package(
                            realms_folder,
                            UPDATE_ZIP_URL,
                            "update",
                            remote_version,
                            on_status=on_status,
                            on_progress_pct=on_progress_pct,
                        )
                        _write_local_version_info(version_file, remote_version, required_aotr)
                    except requests.exceptions.HTTPError as e:
                        if e.response is not None and e.response.status_code == 404:
                            _status(on_status, "Update package not available on server, skipping.", "blue")
                        else:
                            raise
            else:
                # --- Full version path: download complete Realms package ---
                _status(
                    on_status,
                    f"AOTR versions differ (required: {required_aotr}, current: {current_aotr}). "
                    f"Downloading full Realms package...",
                    "blue",
                )
                # Ensure realms folder exists for extraction target
                os.makedirs(realms_folder, exist_ok=True)

                download_and_install_package(
                    realms_folder,
                    FULL_MOD_ZIP_URL,
                    "full version",
                    remote_version,
                    on_status=on_status,
                    on_progress_pct=on_progress_pct,
                )
                _write_local_version_info(version_file, remote_version, required_aotr)
        else:
            # --- Existing install: apply update overlay ---
            if is_lower_version(str(local_version), remote_version):
                _status(on_status, f"Updating from {local_version} to {remote_version}...", "blue")
                try:
                    download_and_install_package(
                        realms_folder,
                        UPDATE_ZIP_URL,
                        "update",
                        remote_version,
                        on_status=on_status,
                        on_progress_pct=on_progress_pct,
                    )
                    _write_local_version_info(version_file, remote_version, required_aotr)
                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code == 404:
                        _status(on_status, "Update package not available on server, skipping.", "blue")
                    else:
                        raise
            else:
                _status(on_status, f"Mod is already up to date ({local_version}).", "green")

        _status(on_status, "Mod installed successfully!", "green")
        return InstallResult(
            success=True,
            installed_version=remote_version,
            realms_folder=realms_folder,
        )
    except Exception as e:
        _status(on_status, f"Error: {e}", "red")
        return InstallResult(success=False, error=str(e))
