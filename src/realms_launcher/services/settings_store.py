from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import winreg

from ..constants import REG_PATH


@dataclass(frozen=True)
class LauncherSettings:
    install_folder: str = ""
    installed: bool = False
    language: str = "English"


def load_settings() -> LauncherSettings:
    """Load persisted settings from HKCU. Returns defaults if missing."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            folder, _ = winreg.QueryValueEx(key, "InstallFolder")
            installed, _ = winreg.QueryValueEx(key, "Installed")
            lang = _try_get_str(key, "Language") or "English"
            return LauncherSettings(
                install_folder=str(folder or ""),
                installed=bool(int(installed)),
                language=str(lang),
            )
    except FileNotFoundError:
        return LauncherSettings()
    except OSError:
        # Corrupt key or access issue; fail safe
        return LauncherSettings()


def save_settings(settings: LauncherSettings) -> None:
    """Persist settings to HKCU."""
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
        winreg.SetValueEx(
            key,
            "InstallFolder",
            0,
            winreg.REG_SZ,
            settings.install_folder or "",
        )
        winreg.SetValueEx(
            key,
            "Installed",
            0,
            winreg.REG_DWORD,
            int(bool(settings.installed)),
        )
        winreg.SetValueEx(
            key,
            "Language",
            0,
            winreg.REG_SZ,
            settings.language or "English",
        )


def update_install_state(*, install_folder: str, installed: bool, language: Optional[str] = None) -> None:
    """Convenience helper to update install folder/state (and optionally language)."""
    current = load_settings()
    save_settings(
        LauncherSettings(
            install_folder=install_folder,
            installed=installed,
            language=language if language is not None else current.language,
        )
    )


def update_language(language: str) -> None:
    current = load_settings()
    save_settings(
        LauncherSettings(
            install_folder=current.install_folder,
            installed=current.installed,
            language=language,
        )
    )


def _try_get_str(key, name: str) -> Optional[str]:
    try:
        v, _ = winreg.QueryValueEx(key, name)
        if v is None:
            return None
        return str(v)
    except OSError:
        return None
