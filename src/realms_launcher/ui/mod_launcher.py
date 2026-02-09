"""ModLauncher composition root (kept intentionally small)."""

from __future__ import annotations

import sys
import tkinter as tk

from ..services import admin_service
from .mixins.actions_mixin import ActionsMixin
from .mixins.admin_mixin import AdminMixin
from .mixins.button_visibility_mixin import ButtonVisibilityMixin
from .mixins.launcher_update_mixin import LauncherUpdateMixin
from .mixins.state_mixin import StateMixin
from .mixins.ui_helpers_mixin import UiHelpersMixin


class ModLauncher(
    tk.Tk,
    AdminMixin,
    UiHelpersMixin,
    StateMixin,
    ButtonVisibilityMixin,
    ActionsMixin,
    LauncherUpdateMixin,
):
    def __init__(self):
        super().__init__()

        is_frozen = getattr(sys, "frozen", False)
        if is_frozen and not admin_service.is_admin():
            self.check_admin_privileges()

        self.title("Age of the Ring: Realms in Exile Launcher")
        self.geometry("800x700")
        self.resizable(False, False)
        self.iconbitmap(self.resource_path("aotr_fs.ico"))

        self.set_custom_cursor(self)

        self.install_folder = tk.StringVar()
        self.is_installed = False
        self.button_shadows = {}

        self.language = tk.StringVar()
        self.language.set("english")

        self.create_background()
        self.create_banner()
        self.create_top_buttons()
        self.create_news_section()
        self.create_bottom_section()

        self.after(100, self.load_last_folder)
        self.check_launcher_update()


if __name__ == "__main__":
    ModLauncher().mainloop()
