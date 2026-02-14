from __future__ import annotations

import os
from tkinter import filedialog, messagebox

from ...constants import BASE_MOD_VERSION
from ...services import news_service, realms_service, settings_service


class StateMixin:
    """Settings persistence + mod status checks + some UI state transitions."""

    def fetch_news(self) -> str:
        try:
            return news_service.fetch_news_html()
        except Exception as e:
            return f"<p>Error: {e}</p>"

    def load_last_folder(self) -> None:
        settings = settings_service.load_settings()
        folder = settings.install_folder
        installed = settings.installed

        try:
            lang = settings.language or "English"
            self.language.set(lang)  # type: ignore[attr-defined]
            lang_l = lang.lower()
            if "english" in lang_l:
                self.language_dropdown.current(0)  # type: ignore[attr-defined]
            elif "portuguese" in lang_l:
                self.language_dropdown.current(1)  # type: ignore[attr-defined]
            else:
                self.language_dropdown.current(0)  # type: ignore[attr-defined]
        except Exception:
            pass

        if folder and os.path.exists(folder):
            if installed:
                self.install_folder.set(folder)  # type: ignore[attr-defined]
                self.is_installed = True  # type: ignore[attr-defined]
                self.folder_label.config(text=f"Installation Folder: {folder}")  # type: ignore[attr-defined]
                self.check_for_mod_updates()
            else:
                self.reset_folder()
        else:
            self.reset_folder()

    def reset_folder(self) -> None:
        self.install_folder.set("")  # type: ignore[attr-defined]
        self.is_installed = False  # type: ignore[attr-defined]
        self.status_label.config(  # type: ignore[attr-defined]
            text="No folder saved. Please select an installation folder.",
            fg="red",
        )
        self.folder_label.config(text="Installation Folder: Not selected")  # type: ignore[attr-defined]
        self.hide_download_button()
        self.hide_play_button()
        self.uninstall_button.config(state="disabled")  # type: ignore[attr-defined]
        self.hide_uninstall_button()
        self.language_dropdown.config(state="disabled")  # type: ignore[attr-defined]

    def select_folder(self) -> None:
        folder = filedialog.askdirectory()
        if not folder:
            self.status_label.config(text="Please select an installation folder.", fg="red")  # type: ignore[attr-defined]
            self.hide_download_button()
            self.hide_play_button()
            return

        aotr_folder = os.path.join(folder, "aotr")
        if not os.path.exists(aotr_folder) or not os.path.isdir(aotr_folder):
            messagebox.showwarning(
                "Invalid Folder",
                "The selected folder does not contain an 'aotr' subfolder.\n\n"
                "Please select the correct Age of the Ring folder that contains the 'aotr' subfolder.",
            )
            self.status_label.config(  # type: ignore[attr-defined]
                text="Please select the correct Age of the Ring folder.",
                fg="red",
            )
            self.hide_download_button()
            self.hide_play_button()
            return

        self.install_folder.set(folder)  # type: ignore[attr-defined]
        self.folder_label.config(text=f"Installation Folder: {folder}")  # type: ignore[attr-defined]
        self.save_folder(folder, installed=False)
        self.status_label.config(text="Checking mod status...", fg="blue")  # type: ignore[attr-defined]
        self.check_for_mod_updates()

    def save_folder(self, folder: str, installed: bool) -> None:
        try:
            settings_service.save_settings(
                install_folder=folder,
                installed=bool(installed),
                language=str(self.language.get() or "English"),  # type: ignore[attr-defined]
            )
        except Exception as e:
            print(f"Error saving settings: {e}")

    def check_for_mod_updates(self) -> None:
        if hasattr(self, "download_button"):
            self.download_button.config(text="Checking...", state="disabled")  # type: ignore[attr-defined]
            self.update_download_button_icon("Checking...")
            self.show_download_button()

        install_path = self.install_folder.get()  # type: ignore[attr-defined]
        try:
            status = realms_service.get_mod_status(install_path)
        except Exception as e:
            self._set_retry_state(f"Error: {e}")
            return

        if status.state == "check_failed":
            self._set_retry_state("Failed to check for updates.")
            return

        self.is_installed = status.installed  # type: ignore[attr-defined]
        remote_version = status.remote_version or BASE_MOD_VERSION
        local_version = status.local_version

        if status.state == "not_installed":
            self.status_label.config(  # type: ignore[attr-defined]
                text=f"Ready to download version {remote_version}.",
                fg="green",
            )
            self.download_button.config(text="Download Mod", state="normal")  # type: ignore[attr-defined]
            self.update_download_button_icon("Download Mod")
            self.show_download_button()
            self.hide_play_button()
            self.uninstall_button.config(state="disabled")  # type: ignore[attr-defined]
            self.hide_uninstall_button()
            self.show_folder_button()
            self.language_dropdown.config(state="disabled")  # type: ignore[attr-defined]
        elif status.state == "update_available":
            self.status_label.config(  # type: ignore[attr-defined]
                text=f"Update available: {remote_version} (Installed: {local_version})",
                fg="orange",
            )
            self.download_button.config(text="Download Update", state="normal")  # type: ignore[attr-defined]
            self.update_download_button_icon("Download Update")
            self.show_download_button()
            self.hide_play_button()
            self.uninstall_button.config(state="normal")  # type: ignore[attr-defined]
            self.show_uninstall_button()
            self.hide_folder_button()
            self.language_dropdown.config(state="readonly")  # type: ignore[attr-defined]
        else:
            self.status_label.config(  # type: ignore[attr-defined]
                text=f"Mod is up-to-date ({local_version}).",
                fg="green",
            )
            self.hide_download_button()
            self.show_play_button()
            self.uninstall_button.config(state="normal")  # type: ignore[attr-defined]
            self.show_uninstall_button()
            self.hide_folder_button()
            self.language_dropdown.config(state="readonly")  # type: ignore[attr-defined]

    def _set_retry_state(self, msg: str) -> None:
        self.status_label.config(text=msg, fg="red")  # type: ignore[attr-defined]
        self.download_button.config(text="Retry", state="normal")  # type: ignore[attr-defined]
        self.update_download_button_icon("Retry")
        self.show_download_button()
        self.hide_play_button()
        self.uninstall_button.config(state="disabled")  # type: ignore[attr-defined]
        self.hide_uninstall_button()
        self.language_dropdown.config(state="disabled")  # type: ignore[attr-defined]
        self.is_installed = False  # type: ignore[attr-defined]

