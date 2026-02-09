from __future__ import annotations

# flake8: noqa

from dataclasses import dataclass
import json
import os
import shutil
from collections.abc import Callable

import rarfile
import requests

from ..constants import (
    AOTR_RAR_URL,
    BASE_MOD_VERSION,
    BASE_MOD_ZIP_URL,
    UPDATE_ZIP_URL,
)
from . import install_service
from .aotr_service import get_aotr_version_from_lotr_str
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
    """Download and install a specific package (realms base/update)."""
    if version_label == "base mod":
        _status(on_status, f"Downloading Realms in Exile version {version_number}...", "blue")
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


def get_aotr_version_info() -> dict[str, str]:
    """Fetch AOTR required version from remote metadata."""
    try:
        info = fetch_remote_version_info()
        return {
            "required_aotr_version": info.required_aotr_version,
            "current_aotr_version": "0.0.0",
        }
    except Exception:
        return {"required_aotr_version": "0.0.0", "current_aotr_version": "0.0.0"}


def get_aotr_version_from_str_file(install_path: str, *, preferred_language: str = "") -> str:
    return get_aotr_version_from_lotr_str(install_path, preferred_language=preferred_language)


def check_aotr_version(
    install_path: str,
    *,
    preferred_language: str = "",
    on_status: StatusCallback | None = None,
    on_progress_pct: ProgressCallback | None = None,
) -> tuple[bool, str | None]:
    """Check if AOTR is compatible; download/extract if not. Returns (updated, rar_path)."""
    try:
        aotr_info = get_aotr_version_info()
        required_version = aotr_info["required_aotr_version"]
        current_version = get_aotr_version_from_str_file(install_path, preferred_language=preferred_language)

        if is_lower_version(current_version, required_version):
            existing_rar_path = os.path.join(install_path, "aotr.rar")
            if os.path.exists(existing_rar_path):
                _status(on_status, "Found existing AOTR RAR file. Extracting...", "blue")
                return True, existing_rar_path

            _status(
                on_status,
                f"Realms in Exile requires AOTR {required_version}. Current version: {current_version}. Downloading...",
                "blue",
            )
            rar_path = download_and_install_aotr(
                install_path,
                required_version,
                preferred_language=preferred_language,
                on_status=on_status,
                on_progress_pct=on_progress_pct,
            )
            return True, rar_path

        return False, None
    except Exception:
        return False, None


def download_and_install_aotr(
    install_path: str,
    aotr_version: str,
    *,
    preferred_language: str = "",
    on_status: StatusCallback | None = None,
    on_progress_pct: ProgressCallback | None = None,
) -> str | None:
    """Download AOTR RAR, extract into realms folder, return rar path (or None if deleted)."""
    # Create a temporary file name
    rar_path = os.path.join(install_path, "aotr.rar")

    r = requests.get(AOTR_RAR_URL, stream=True)
    total_size = int(r.headers.get("content-length", 0))
    downloaded_size = 0

    with open(rar_path, "wb") as file:
        for chunk in r.iter_content(chunk_size=1024):
            if not chunk:
                continue
            file.write(chunk)
            downloaded_size += len(chunk)
            if total_size > 0:
                _progress(on_progress_pct, (downloaded_size / total_size) * 100.0)

    _status(on_status, "Installing AOTR...", "blue")

    realms_folder = os.path.join(install_path, "realms")
    if os.path.exists(realms_folder):
        _status(on_status, "Removing existing realms folder...", "blue")
        shutil.rmtree(realms_folder)

    try:
        with rarfile.RarFile(rar_path, "r") as rar_ref:
            rar_ref.extractall(install_path)

            extracted_aotr = os.path.join(install_path, "aotr")
            if os.path.exists(extracted_aotr):
                os.rename(extracted_aotr, realms_folder)
            else:
                os.makedirs(realms_folder, exist_ok=True)
                for item in os.listdir(install_path):
                    item_path = os.path.join(install_path, item)
                    if os.path.isfile(item_path) and item != "aotr.rar":
                        shutil.move(item_path, os.path.join(realms_folder, item))
                    elif os.path.isdir(item_path) and item != "realms":
                        shutil.move(item_path, os.path.join(realms_folder, item))

        _status(on_status, f"AOTR version {aotr_version} extracted successfully", "green")
    except Exception as rar_error:
        _status(on_status, "RAR extraction failed, checking AOTR version...", "orange")

        # Helpful message (stdout only)
        if "Cannot find working tool" in str(rar_error):
            print("Note: To extract RAR files, install a RAR extraction tool like:")
            print("  - WinRAR: https://www.win-rar.com/")
            print("  - 7-Zip: https://7-zip.org/")
            print("  - Or use the command line: choco install unrar")

        aotr_info = get_aotr_version_info()
        required_version = aotr_info["required_aotr_version"]
        current_version = get_aotr_version_from_str_file(install_path, preferred_language=preferred_language)

        if is_lower_version(current_version, required_version):
            raise Exception(
                f"RAR extraction failed. Current AOTR version ({current_version}) is lower than required ({required_version}). "
                f"Please install a RAR extraction tool to proceed."
            )

        existing_aotr = os.path.join(install_path, "aotr")
        if os.path.exists(existing_aotr):
            shutil.copytree(existing_aotr, realms_folder)
            _status(on_status, "Using existing AOTR folder as fallback", "green")
        else:
            raise Exception("RAR extraction failed and no existing AOTR folder found")

        # Delete the downloaded RAR file since we couldn't use it
        try:
            if os.path.exists(rar_path):
                os.remove(rar_path)
        except Exception:
            pass
        return None

    _status(on_status, f"AOTR version {aotr_version} installed successfully", "green")
    return rar_path


def install_or_update_realms(
    install_path: str,
    *,
    preferred_language: str = "",
    on_status: StatusCallback | None = None,
    on_progress_pct: ProgressCallback | None = None,
) -> InstallResult:
    """Main workflow: ensure AOTR compatibility, then install base/update realms."""
    try:
        install_path = os.path.normpath(install_path)
        existing_rar_path = os.path.join(install_path, "aotr.rar")

        aotr_updated, aotr_rar_path = check_aotr_version(
            install_path,
            preferred_language=preferred_language,
            on_status=on_status,
            on_progress_pct=on_progress_pct,
        )

        # If we found an existing RAR file, we need to extract it if realms folder missing
        if aotr_updated and aotr_rar_path and os.path.exists(aotr_rar_path):
            realms_folder = os.path.join(install_path, "realms")
            if not os.path.exists(realms_folder) or not os.path.isdir(realms_folder):
                _status(on_status, "Extracting existing AOTR RAR file...", "blue")
                try:
                    with rarfile.RarFile(aotr_rar_path, "r") as rar_ref:
                        rar_ref.extractall(install_path)
                        extracted_aotr = os.path.join(install_path, "aotr")
                        if os.path.exists(extracted_aotr):
                            os.rename(extracted_aotr, realms_folder)
                        else:
                            os.makedirs(realms_folder, exist_ok=True)
                            for item in os.listdir(install_path):
                                item_path = os.path.join(install_path, item)
                                if os.path.isfile(item_path) and item != "aotr.rar":
                                    shutil.move(item_path, os.path.join(realms_folder, item))
                                elif os.path.isdir(item_path) and item != "realms":
                                    shutil.move(item_path, os.path.join(realms_folder, item))
                    _status(on_status, "Successfully extracted existing AOTR RAR file", "green")
                except Exception as extract_error:
                    print(f"Failed to extract existing RAR file: {extract_error}")
                    _status(on_status, "Failed to extract existing RAR file, continuing...", "orange")
                    aotr_updated = False
                    aotr_rar_path = None

        if not aotr_rar_path and os.path.exists(existing_rar_path):
            aotr_rar_path = existing_rar_path
            print(f"Found existing AOTR RAR file: {existing_rar_path}")

        realms_folder = os.path.join(install_path, "realms")
        if aotr_rar_path and os.path.exists(aotr_rar_path) and (not os.path.exists(realms_folder) or not os.path.isdir(realms_folder)):
            _status(on_status, "Attempting to extract existing AOTR RAR file...", "blue")
            try:
                with rarfile.RarFile(aotr_rar_path, "r") as rar_ref:
                    rar_ref.extractall(install_path)
                    extracted_aotr = os.path.join(install_path, "aotr")
                    if os.path.exists(extracted_aotr):
                        os.rename(extracted_aotr, realms_folder)
                    else:
                        os.makedirs(realms_folder, exist_ok=True)
                        for item in os.listdir(install_path):
                            item_path = os.path.join(install_path, item)
                            if os.path.isfile(item_path) and item != "aotr.rar":
                                shutil.move(item_path, os.path.join(realms_folder, item))
                            elif os.path.isdir(item_path) and item != "realms":
                                shutil.move(item_path, os.path.join(realms_folder, item))
                _status(on_status, "Successfully extracted existing AOTR RAR file", "green")
                aotr_updated = True
            except Exception as extract_error:
                print(f"Failed to extract existing RAR file: {extract_error}")
                _status(on_status, "Failed to extract existing RAR file, continuing...", "orange")

        # Get remote version for comparison
        try:
            remote_version = fetch_remote_version_info().version
        except Exception:
            remote_version = "0.0.0"

        version_file = os.path.join(realms_folder, "realms_version.json")
        is_update = False
        needs_base_first = False
        local_version = "not installed"

        if os.path.exists(version_file):
            try:
                with open(version_file, "r", encoding="utf-8") as file:
                    content = file.read().strip()
                    if content:
                        local_version = json.loads(content).get("version", "unknown")
                        is_update = True
                        if is_lower_version(str(local_version), BASE_MOD_VERSION):
                            needs_base_first = True
            except Exception:
                is_update = False
        else:
            needs_base_first = True

        if not os.path.exists(version_file) or needs_base_first:
            if not aotr_updated:
                realms_folder = prepare_realms_folder(install_path, on_status=on_status)

        if not os.path.exists(realms_folder) or not os.path.isdir(realms_folder):
            raise Exception("Realms folder not found. AOTR extraction failed and no fallback available.")

        if needs_base_first:
            _status(on_status, f"Installing base version {BASE_MOD_VERSION}...", "blue")
            download_and_install_package(
                realms_folder,
                BASE_MOD_ZIP_URL,
                "base mod",
                BASE_MOD_VERSION,
                on_status=on_status,
                on_progress_pct=on_progress_pct,
            )

            with open(version_file, "w", encoding="utf-8") as file:
                json.dump({"version": BASE_MOD_VERSION}, file)

            if is_lower_version(BASE_MOD_VERSION, remote_version):
                _status(on_status, f"Base version installed. Now updating to version {remote_version}...", "blue")
                download_and_install_package(
                    realms_folder,
                    UPDATE_ZIP_URL,
                    "update",
                    remote_version,
                    on_status=on_status,
                    on_progress_pct=on_progress_pct,
                )
                with open(version_file, "w", encoding="utf-8") as file:
                    json.dump({"version": remote_version}, file)
        else:
            download_url = UPDATE_ZIP_URL if is_update else BASE_MOD_ZIP_URL
            version_label = "update" if is_update else "base mod"
            version_number = remote_version if is_update else BASE_MOD_VERSION

            download_and_install_package(
                realms_folder,
                download_url,
                version_label,
                version_number,
                on_status=on_status,
                on_progress_pct=on_progress_pct,
            )
            with open(version_file, "w", encoding="utf-8") as file:
                json.dump({"version": remote_version if is_update else BASE_MOD_VERSION}, file)

        # Delete AOTR rar after successful realms install
        if aotr_rar_path and os.path.exists(aotr_rar_path):
            try:
                if os.path.exists(realms_folder) and os.path.isdir(realms_folder):
                    os.remove(aotr_rar_path)
                    print(f"Deleted AOTR RAR file: {aotr_rar_path}")
            except Exception as e:
                print(f"Warning: Could not delete AOTR RAR file: {e}")

        _status(on_status, "Mod installed successfully!", "green")
        return InstallResult(
            success=True,
            installed_version=remote_version,
            realms_folder=realms_folder,
        )
    except Exception as e:
        _status(on_status, f"Error: {e}", "red")
        return InstallResult(success=False, error=str(e))
