from __future__ import annotations

import os
import shutil
import subprocess


def launch_game(install_path: str) -> None:
    """Launch BFME2 RotWK with -mod pointing at realms folder."""
    install_path = os.path.normpath(install_path)
    rotwk_folder = os.path.join(install_path, "rotwk")
    game_executable = os.path.normpath(
        os.path.join(rotwk_folder, "lotrbfme2ep1.exe")
    )
    if not os.path.exists(game_executable):
        raise FileNotFoundError(game_executable)

    mod_folder = os.path.join(install_path, "realms")

    # Copy dxvk.conf from realms/dxvk/ to rotwk/ if it exists
    dxvk_source = os.path.join(mod_folder, "dxvk", "dxvk.conf")
    dxvk_dest = os.path.join(rotwk_folder, "dxvk.conf")
    if os.path.exists(dxvk_source):
        try:
            shutil.copy2(dxvk_source, dxvk_dest)
        except Exception:
            # Best-effort only
            pass

    cmd = f'"{game_executable}" -mod "{mod_folder}"'
    subprocess.Popen(cmd, shell=True)
