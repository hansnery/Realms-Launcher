from __future__ import annotations

from tkinter import messagebox

from ...constants import LAUNCHER_VERSION, LAUNCHER_ZIP_URL
from ...services import launcher_update_service
from ...services.version_service import fetch_remote_version_info, is_latest_newer


class LauncherUpdateMixin:
    """Launcher self-update flow (download+stage+spawn updater)."""

    def check_launcher_update(self) -> None:
        try:
            info = fetch_remote_version_info()
            latest_launcher_version = info.launcher_version

            if is_latest_newer(LAUNCHER_VERSION, latest_launcher_version):
                user_choice = messagebox.askyesno(
                    "Launcher Update Available",
                    f"A new launcher version ({latest_launcher_version}) is available. Download and apply now?",
                )
                if user_choice:
                    self.update_launcher()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check for launcher updates: {e}")

    def update_launcher(self) -> None:
        self.set_ani_cursor(self)  # type: ignore[arg-type]
        self.set_ani_cursor(self.bg_canvas)  # type: ignore[attr-defined]

        try:
            self.enter_update_mode()
            self.status_label.config(text="Preparing launcher update...", fg="blue")  # type: ignore[attr-defined]
            self.update()  # type: ignore[attr-defined]

            def _on_status(msg: str):
                self.status_label.config(text=msg, fg="blue")  # type: ignore[attr-defined]
                self.update()  # type: ignore[attr-defined]

            def _on_progress(pct: float):
                self.bg_canvas.itemconfig(self.progress_window, state="normal")  # type: ignore[attr-defined]
                self.progress["value"] = pct  # type: ignore[attr-defined]
                self.update()  # type: ignore[attr-defined]

            staged_dir = launcher_update_service.download_and_stage_zip(
                LAUNCHER_ZIP_URL,
                on_status=_on_status,
                on_progress_pct=_on_progress,
            )

            launcher_update_service.spawn_updater_and_quit(
                staged_dir=staged_dir,
                quit_callback=lambda: self.after(300, self._quit_for_update),  # type: ignore[attr-defined]
                on_status=_on_status,
            )
        except Exception as e:
            messagebox.showerror("Update Failed", f"Failed to update the launcher: {e}")
            try:
                self.bg_canvas.itemconfig(self.progress_window, state="hidden")  # type: ignore[attr-defined]
            except Exception:
                pass
            self.exit_update_mode()

    def enter_update_mode(self) -> None:
        self.is_updating = True  # type: ignore[attr-defined]
        self.hide_play_button()

        for w in (self.folder_button, self.uninstall_button, self.language_dropdown):  # type: ignore[attr-defined]
            try:
                w.config(state="disabled")
            except Exception:
                pass
        try:
            self.download_button.config(state="disabled")  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            self.bg_canvas.itemconfig(self.progress_window, state="normal")  # type: ignore[attr-defined]
        except Exception:
            pass

    def exit_update_mode(self) -> None:
        self.is_updating = False  # type: ignore[attr-defined]
        try:
            self.show_play_button()
        except Exception:
            pass
        for w in (self.folder_button, self.uninstall_button, self.language_dropdown):  # type: ignore[attr-defined]
            try:
                w.config(state="normal")
            except Exception:
                pass
        try:
            self.download_button.config(state="normal")  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            self.bg_canvas.itemconfig(self.progress_window, state="hidden")  # type: ignore[attr-defined]
        except Exception:
            pass

