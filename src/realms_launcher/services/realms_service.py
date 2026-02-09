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


def _local_version_from_file(version_file: str) -> str | None:
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return None
        data = json.loads(content) or {}
        v = data.get("version")
        return str(v) if v else None
    except Exception:
        return None


def get_mod_status(install_path: str) -> ModStatus:
    """Compute mod install/update status without touching UI."""
    install_path = os.path.normpath(install_path or "")
    realms_folder = os.path.join(install_path, "realms")
    version_file = os.path.join(realms_folder, "realms_version.json")

    local_version = _local_version_from_file(version_file)

    try:
        info = fetch_remote_version_info()
        remote_version = info.version
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

    if str(local_version) != str(remote_version):
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

