from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Literal

from .version_service import fetch_remote_version_info


State = Literal["not_installed", "update_available", "up_to_date", "check_failed"]


@dataclass(frozen=True)
class ModStatus:
    state: State
    install_path: str
    realms_folder: str
    local_version: str
    remote_version: str | None
    error: str | None = None

    @property
    def installed(self) -> bool:
        return self.state in ("update_available", "up_to_date")

    @property
    def update_available(self) -> bool:
        return self.state == "update_available"


def _local_version_info(version_file: str) -> tuple[str | None, str | None]:
    """Read local version and aotr_version from realms_version.json.

    Returns (version, aotr_version) — either may be None.
    """
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return None, None
        data = json.loads(content) or {}
        v = data.get("version")
        a = data.get("aotr_version")
        return (str(v) if v else None, str(a) if a else None)
    except Exception:
        return None, None


def get_mod_status(install_path: str) -> ModStatus:
    """Compute mod install/update status without touching UI.

    Also checks whether the local AOTR base version still matches the cloud's
    required_aotr_version.  If it differs the mod is treated as needing a
    reinstall (reported as ``update_available``).
    """
    install_path = os.path.normpath(install_path or "")
    realms_folder = os.path.join(install_path, "realms")
    version_file = os.path.join(realms_folder, "realms_version.json")

    local_version, local_aotr_version = _local_version_info(version_file)

    try:
        info = fetch_remote_version_info()
        remote_version = info.version
        required_aotr = info.required_aotr_version
    except Exception as e:
        return ModStatus(
            state="check_failed",
            install_path=install_path,
            realms_folder=realms_folder,
            local_version=local_version or "not installed",
            remote_version=None,
            error=str(e),
        )

    if not local_version:
        return ModStatus(
            state="not_installed",
            install_path=install_path,
            realms_folder=realms_folder,
            local_version="not installed",
            remote_version=remote_version,
        )

    # If the AOTR base changed, treat as needing reinstall
    aotr_base_changed = (
        local_aotr_version is not None
        and local_aotr_version != required_aotr
    )

    if aotr_base_changed or str(local_version) != str(remote_version):
        return ModStatus(
            state="update_available",
            install_path=install_path,
            realms_folder=realms_folder,
            local_version=str(local_version),
            remote_version=str(remote_version),
        )

    return ModStatus(
        state="up_to_date",
        install_path=install_path,
        realms_folder=realms_folder,
        local_version=str(local_version),
        remote_version=str(remote_version),
    )

