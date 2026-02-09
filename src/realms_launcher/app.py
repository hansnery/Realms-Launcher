"""Application entry wiring (Tk root)."""

from __future__ import annotations

from .ui.window import ModLauncher


def create_app() -> ModLauncher:
    return ModLauncher()
