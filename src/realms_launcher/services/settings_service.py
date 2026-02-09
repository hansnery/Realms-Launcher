from __future__ import annotations

from dataclasses import dataclass

import winreg

from ..constants import REG_PATH


@dataclass(frozen=True)
class LauncherSettings:
    install_folder: str = ""
    installed: bool = False
    language: str = "English"


def load_settings(reg_path: str = REG_PATH) -> LauncherSettings:
    """Load launcher settings from HKCU registry (best-effort)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            folder, _ = winreg.QueryValueEx(key, "InstallFolder")
            installed, _ = winreg.QueryValueEx(key, "Installed")
            try:
                language, _ = winreg.QueryValueEx(key, "Language")
            except Exception:
                language = "English"
            return LauncherSettings(
                install_folder=str(folder or ""),
                installed=bool(int(installed)),
                language=str(language or "English"),
            )
    except FileNotFoundError:
        return LauncherSettings()
    except Exception:
        return LauncherSettings()


def save_settings(
    *,
    install_folder: str,
    installed: bool,
    language: str,
    reg_path: str = REG_PATH,
) -> None:
    """Persist launcher settings to HKCU registry (best-effort)."""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            winreg.SetValueEx(key, "InstallFolder", 0, winreg.REG_SZ, str(install_folder or ""))
            winreg.SetValueEx(key, "Installed", 0, winreg.REG_DWORD, int(bool(installed)))
            winreg.SetValueEx(key, "Language", 0, winreg.REG_SZ, str(language or "English"))
    except Exception:
        # Best-effort only; UI will continue without persistence.
        return


def save_language(language: str, reg_path: str = REG_PATH) -> None:
    """Update only the language key (best-effort)."""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            winreg.SetValueEx(key, "Language", 0, winreg.REG_SZ, str(language or "English"))
    except Exception:
        return

