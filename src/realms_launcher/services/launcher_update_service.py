from __future__ import annotations

import os
import pathlib
import tempfile
import time
from collections.abc import Callable
from zipfile import ZipFile

import ctypes

from ..constants import USE_ELEVATED_UPDATER
from ..util.runtime import (
    can_write_to_dir,
    is_frozen,
    launcher_dir,
    launcher_path,
    start_detached,
)
from .updater_scripts import write_updater_cmd, write_updater_ps1


StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[float], None]  # 0-100


def download_and_stage_zip(
    url: str,
    *,
    on_status: StatusCallback | None = None,
    on_progress_pct: ProgressCallback | None = None,
) -> str:
    """Download and extract update zip into a staging folder.

    Returns the folder that contains the launcher files to copy.
    """
    temp_root = tempfile.mkdtemp(prefix="realms_launcher_update_")
    zip_path = os.path.join(temp_root, "update.zip")

    if on_status:
        on_status("Downloading launcher update...")
    if on_progress_pct:
        on_progress_pct(0)

    import requests

    r = requests.get(url, stream=True)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0) or 0)
    got = 0
    with open(zip_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 14):
            if not chunk:
                continue
            f.write(chunk)
            got += len(chunk)
            if on_progress_pct and total:
                on_progress_pct(got * 100 / total)

    if on_status:
        on_status("Staging launcher update...")

    staged_dir = os.path.join(temp_root, "staged")
    os.makedirs(staged_dir, exist_ok=True)
    with ZipFile(zip_path, "r") as zf:
        zf.extractall(staged_dir)

    # If zip contains a top-level folder, descend into it
    entries = list(pathlib.Path(staged_dir).iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        staged_dir = str(entries[0])

    # If update zip contains nested folders, find folder containing the exe
    try:
        exe_basename = (
            os.path.basename(launcher_path()) if is_frozen() else "realms_launcher.exe"
        )
        found_parent = None
        for root, _dirs, files in os.walk(staged_dir):
            if exe_basename in files:
                found_parent = root
                break
        if found_parent and os.path.normpath(found_parent) != os.path.normpath(staged_dir):
            staged_dir = found_parent
    except Exception:
        pass

    return staged_dir


def spawn_updater_and_quit(
    *,
    staged_dir: str,
    quit_callback: Callable[[], None],
    on_status: StatusCallback | None = None,
) -> None:
    """Write updater scripts, launch updater (elevated if needed), then quit."""
    temp_root = os.path.dirname(os.path.dirname(staged_dir))  # parent of 'staged'
    ps1_path = os.path.join(temp_root, "do_update.ps1")
    cmd_path = os.path.join(temp_root, "do_update.cmd")
    write_updater_ps1(ps1_path)
    write_updater_cmd(cmd_path)

    target_dir = launcher_dir()
    log_path = os.path.join(tempfile.gettempdir(), "realms_launcher_update.log")
    try:
        with open(log_path, "a", encoding="utf-8") as lf:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            lf.write(f"[python] starting update at {ts}\n")
    except Exception:
        pass

    if is_frozen():
        relaunch_path = launcher_path()
        relaunch_args = ""
    else:
        import sys

        relaunch_path = sys.executable
        relaunch_args = f'\"{os.path.abspath(sys.argv[0])}\"'

    relaunch_cwd = target_dir

    cmd_args = [
        "/c",
        cmd_path,
        target_dir,
        staged_dir,
        str(os.getpid()),
        relaunch_path,
        relaunch_args,
        relaunch_cwd,
        log_path,
    ]

    use_elevated = USE_ELEVATED_UPDATER or (not can_write_to_dir(target_dir))
    if use_elevated:
        if on_status:
            on_status("Requesting Windows permission to update...")

        def _join_cmd_args(args: list[str]) -> str:
            out: list[str] = []
            for a in args:
                if a is None:
                    continue
                out.append('"' + a.replace('"', '""') + '"')
            return " ".join(out)

        arg_string = _join_cmd_args(cmd_args)
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "cmd.exe",
            arg_string,
            None,
            1,
        )
    else:
        start_detached(["cmd.exe"] + cmd_args)

    if on_status:
        on_status("Applying update... The launcher will close and reopen.")
    quit_callback()

