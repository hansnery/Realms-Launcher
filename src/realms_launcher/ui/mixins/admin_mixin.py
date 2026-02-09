from __future__ import annotations

import os
import sys
from tkinter import messagebox

from ...services import admin_service


class AdminMixin:
    """Admin privilege helpers + controlled quit for self-update."""

    def _quit_for_update(self) -> None:
        # Stop Tk event loop and exit so updater can replace files
        try:
            self.destroy()  # type: ignore[attr-defined]
        except Exception:
            pass
        os._exit(0)

    def check_admin_privileges(self) -> None:
        """Check if running with admin privileges and prompt user if not."""
        if admin_service.is_admin():
            return

        result = messagebox.askyesno(
            "Admin Privileges Required",
            "This launcher requires administrator privileges to function properly.\n\n"
            "Would you like to restart the application with admin privileges?\n\n"
            "Note: This will close the current instance and restart with elevated permissions.",
            icon="warning",
        )

        if result:
            if admin_service.run_as_admin():
                try:
                    self.quit()  # type: ignore[attr-defined]
                except Exception:
                    pass
                sys.exit(0)

            messagebox.showerror(
                "Error",
                "Failed to restart with admin privileges.\n"
                "Please run the launcher as administrator manually.",
            )
        else:
            messagebox.showwarning(
                "Limited Functionality",
                "The launcher will continue without admin privileges.\n"
                "Some features may not work correctly.\n\n"
                "To ensure full functionality, please run the launcher as administrator.",
            )

