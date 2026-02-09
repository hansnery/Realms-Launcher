from __future__ import annotations

import ctypes
import sys


def is_admin() -> bool:
    """Check if the application is running with admin privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin() -> bool:
    """Restart the application with admin privileges."""
    try:
        if getattr(sys, "frozen", False):
            script = sys.executable
        else:
            script = sys.argv[0]

        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            script,
            None,
            1,
        )
        return True
    except Exception:
        return False
