from __future__ import annotations

import json
import os
import re

import winshell


def create_shortcut_for_install(install_path: str) -> str:
    """Create desktop shortcut for launching realms. Returns shortcut path."""
    install_path = os.path.normpath(install_path)
    rotwk_folder = os.path.join(install_path, "rotwk")
    game_executable = os.path.normpath(
        os.path.join(rotwk_folder, "lotrbfme2ep1.exe")
    )
    if not os.path.exists(game_executable):
        raise FileNotFoundError(game_executable)

    mod_folder = os.path.join(install_path, "realms")
    icon_path = os.path.normpath(os.path.join(mod_folder, "aotr_fs.ico"))
    if not os.path.exists(icon_path):
        raise FileNotFoundError(icon_path)

    version_file = os.path.join(mod_folder, "realms_version.json")
    mod_version = "unknown"
    if os.path.exists(version_file):
        try:
            with open(version_file, "r", encoding="utf-8") as f:
                mod_version = json.load(f).get("version", "unknown")
        except Exception:
            mod_version = "unknown"

    desktop = os.path.normpath(os.path.join(os.environ["USERPROFILE"], "Desktop"))
    shortcut_name = f"Realms in Exile v{mod_version}.lnk"
    shortcut_path = os.path.join(desktop, shortcut_name)

    arguments = f'-mod "{mod_folder}"'
    with winshell.shortcut(shortcut_path) as shortcut:
        shortcut.path = game_executable
        shortcut.arguments = arguments
        shortcut.description = f"Launch Realms in Exile v{mod_version}"
        shortcut.icon_location = (icon_path, 0)

    return shortcut_path


def remove_existing_shortcuts() -> int:
    """Remove all Realms shortcuts from desktop. Returns count removed."""
    desktop = os.path.normpath(os.path.join(os.environ["USERPROFILE"], "Desktop"))
    removed = 0
    for file in os.listdir(desktop):
        if re.match(r"Realms in Exile v.*\.lnk", file):
            try:
                os.remove(os.path.join(desktop, file))
                removed += 1
            except Exception:
                pass
    return removed
