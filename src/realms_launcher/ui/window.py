"""Compatibility import surface for `ModLauncher`.

The full implementation lives in `ui/mod_launcher.py` so this file stays small.
External imports should continue to use:

    from realms_launcher.ui.window import ModLauncher
"""

from __future__ import annotations

from .mod_launcher import ModLauncher

__all__ = ["ModLauncher"]
