from __future__ import annotations

import os
import subprocess
import sys


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def launcher_dir() -> str:
    """Where the launcher lives (EXE dir for frozen, repo root for dev)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    # runtime.py -> util -> realms_launcher -> src -> repo root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def launcher_path() -> str:
    return sys.executable if is_frozen() else os.path.abspath(sys.argv[0])


def can_write_to_dir(directory: str) -> bool:
    try:
        test_path = os.path.join(directory, f".write_test_{os.getpid()}.tmp")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_path)
        return True
    except Exception:
        return False


def start_detached(cmd: "str | list[str]") -> None:
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(
        cmd,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )

