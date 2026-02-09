from __future__ import annotations

import os
import re
import shutil
from tkinter import messagebox

from ...services import game_service, shortcut_service, settings_service


class ActionsMixin:
    """User-triggered actions: language switch, install, launch, uninstall, shortcuts."""

    def change_language(self, event=None) -> None:
        if not getattr(self, "is_installed", False):
            return

        install_path = self.install_folder.get()  # type: ignore[attr-defined]
        if not install_path:
            messagebox.showerror("Error", "No installation folder selected.")
            return

        realms_folder = os.path.join(install_path, "realms")
        data_folder = os.path.join(realms_folder, "data")
        translations_folder = os.path.join(data_folder, "translations")

        target_file = os.path.join(data_folder, "lotr.str")
        selected_language = (self.language.get() or "").lower()  # type: ignore[attr-defined]

        if "english" in selected_language:
            source_folder = os.path.join(translations_folder, "en")
        elif "portuguese" in selected_language:
            source_folder = os.path.join(translations_folder, "pt-br")
        else:
            messagebox.showerror("Error", f"Unsupported language: {selected_language}")
            return

        source_file = os.path.join(source_folder, "lotr.str")
        if not os.path.exists(source_file):
            messagebox.showerror("Error", f"Language file not found: {source_file}")
            return

        try:
            shutil.copy2(source_file, target_file)
            settings_service.save_language(self.language.get())  # type: ignore[attr-defined]
            messagebox.showinfo("Success", f"Language changed to {self.language.get()}")  # type: ignore[attr-defined]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to change language: {e}")

    def download_and_extract_mod(self) -> None:
        install_path = self.install_folder.get()  # type: ignore[attr-defined]
        if not install_path:
            self.status_label.config(text="No installation folder selected.", fg="red")  # type: ignore[attr-defined]
            return

        self.set_ani_cursor(self)  # type: ignore[arg-type]
        self.set_ani_cursor(self.bg_canvas)  # type: ignore[attr-defined]

        try:
            self.hide_folder_button()
            self.hide_download_button()
            self.hide_play_button()
            self.bg_canvas.itemconfig(self.progress_window, state="normal")  # type: ignore[attr-defined]

            def _on_status(msg: str, fg: str = "blue"):
                self.status_label.config(text=msg, fg=fg)  # type: ignore[attr-defined]
                self.update()  # type: ignore[attr-defined]

            def _on_progress(pct: float):
                self.progress["value"] = pct  # type: ignore[attr-defined]
                self.update()  # type: ignore[attr-defined]

            from ...services import realms_install_service

            result = realms_install_service.install_or_update_realms(
                install_path,
                preferred_language=str(self.language.get() or ""),  # type: ignore[attr-defined]
                on_status=_on_status,
                on_progress_pct=_on_progress,
            )
            if not result.success:
                raise Exception(result.error or "Install failed")

            self.uninstall_button.config(state="normal")  # type: ignore[attr-defined]
            self.show_uninstall_button()
            self.create_shortcut_button.config(state="normal")  # type: ignore[attr-defined]
            self.show_create_shortcut_button()
            self.bg_canvas.itemconfig(self.progress_window, state="hidden")  # type: ignore[attr-defined]
            self.save_folder(install_path, installed=True)

            self.show_folder_button()
            self.change_language()
            self.language_dropdown.config(state="readonly")  # type: ignore[attr-defined]
            self.show_play_button()
            self.check_for_mod_updates()
            self.set_custom_cursor(self)  # type: ignore[arg-type]
            self.set_custom_cursor(self.bg_canvas)  # type: ignore[attr-defined]
        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")  # type: ignore[attr-defined]
            self.bg_canvas.itemconfig(self.progress_window, state="hidden")  # type: ignore[attr-defined]
            self.show_download_button()
            self.hide_play_button()
            self.show_folder_button()
            self.set_custom_cursor(self)  # type: ignore[arg-type]
            self.set_custom_cursor(self.bg_canvas)  # type: ignore[attr-defined]

    def launch_game(self) -> None:
        try:
            install_path = self.install_folder.get()  # type: ignore[attr-defined]
            game_service.launch_game(install_path)
            self.iconify()  # type: ignore[attr-defined]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch the game: {e}")

    def uninstall_mod(self) -> None:
        folder = self.install_folder.get()  # type: ignore[attr-defined]
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "No valid installation folder selected.")
            return

        if not messagebox.askyesno(
            "Confirm Uninstall",
            "Do you really want to uninstall the Realms in Exile mod? This will not delete your Age of the Ring mod.",
        ):
            return

        try:
            realms_folder = os.path.join(folder, "realms")
            if os.path.exists(realms_folder):
                shutil.rmtree(realms_folder)

            desktop = os.path.normpath(os.path.join(os.environ["USERPROFILE"], "Desktop"))
            for file in os.listdir(desktop):
                if re.match(r"Realms in Exile v.*\\.lnk", file):
                    os.remove(os.path.join(desktop, file))

            self.status_label.config(  # type: ignore[attr-defined]
                text="Mod uninstalled successfully. All files and folders were removed.",
                fg="green",
            )
            self.folder_label.config(text="Installation Folder: Not selected")  # type: ignore[attr-defined]
            self.install_folder.set("")  # type: ignore[attr-defined]
            self.save_folder("", installed=False)

            self.hide_download_button()
            self.hide_play_button()
            self.uninstall_button.config(state="disabled")  # type: ignore[attr-defined]
            self.hide_uninstall_button()
            self.create_shortcut_button.config(state="disabled")  # type: ignore[attr-defined]
            self.hide_create_shortcut_button()
            self.show_folder_button()
            self.language_dropdown.config(state="disabled")  # type: ignore[attr-defined]
        except Exception as e:
            self.status_label.config(text=f"Error uninstalling mod: {e}", fg="red")  # type: ignore[attr-defined]

    def create_shortcut(self) -> None:
        try:
            install_path = self.install_folder.get()  # type: ignore[attr-defined]
            shortcut_path = shortcut_service.create_shortcut_for_install(install_path)
            messagebox.showinfo(
                "Shortcut Created",
                f"Shortcut created on the desktop: {shortcut_path}",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create shortcut: {e}")

