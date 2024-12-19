import os
import sys
import json
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from zipfile import ZipFile
from tkinter import ttk
import requests
from PIL import Image, ImageTk
import winreg
import re
from tkhtmlview import HTMLLabel
import shutil  # Import shutil for removing directories

# Constants
MOD_INFO_URL = "https://storage.googleapis.com/realms-in-exile/updater/version.json"
MOD_ZIP_URL = "https://storage.googleapis.com/realms-in-exile/updater/realms_beta.zip"
NEWS_URL = "https://raw.githubusercontent.com/hansnery/Realms-Launcher/refs/heads/main/news.html"
LAUNCHER_VERSION = "1.0.0"
REG_PATH = r"SOFTWARE\REALMS_Launcher"

class Tooltip:
    """A simple tooltip class for Tkinter widgets."""
    def __init__(self, widget, text=""):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        """Display the tooltip near the widget."""
        x = event.x_root + 10
        y = event.y_root + 10

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)  # Remove window decorations
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background="lightyellow",
            relief="solid",
            borderwidth=1,
            font=("Arial", 10)
        )
        label.pack()

    def hide_tooltip(self, event):
        """Hide the tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class ModLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Age of the Ring: Realms in Exile Launcher")
        self.geometry("600x500")
        self.resizable(False, False)
        self.iconbitmap("aotr_fs.ico")

        # Selected folder and mod state
        self.install_folder = tk.StringVar()
        self.is_installed = False

        # Layout Frames
        self.create_banner()
        self.create_top_buttons()
        self.create_news_section()
        self.create_bottom_section()

        # Load last folder and check mod version
        self.after(100, self.load_last_folder)

    def create_banner(self):
        """Displays the banner at the top."""
        try:
            image = Image.open("banner.png")
            image = image.resize((600, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            banner = tk.Label(self, image=photo)
            banner.image = photo
            banner.pack()
        except Exception as e:
            print(f"Error loading banner: {e}")

    def create_top_buttons(self):
        """Creates top buttons for folder selection, uninstallation, and creating shortcuts."""
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(pady=10)

        # Use pack for consistent geometry management
        self.folder_button = tk.Button(self.top_frame, text="Select Install Folder", command=self.select_folder)
        self.folder_button.pack(side="left", padx=10, pady=5)
        Tooltip(self.folder_button, "Install it in a copy of the 'aotr' folder of the Age of the Ring mod.")

        self.uninstall_button = tk.Button(self.top_frame, text="Uninstall Mod", command=self.uninstall_mod, state="disabled")
        self.uninstall_button.pack(side="left", padx=10, pady=5)
        Tooltip(self.uninstall_button, "Remove the mod and delete all its files and folders.")

        self.create_shortcut_button = tk.Button(self.top_frame, text="Create Shortcut", command=self.create_shortcut, state="disabled")
        self.create_shortcut_button.pack(side="left", padx=10, pady=5)
        Tooltip(self.create_shortcut_button, "Create a desktop shortcut to launch the mod.")

    def create_news_section(self):
        """Creates the news section in the middle."""
        self.news_frame = tk.Frame(self, borderwidth=2, relief="groove", height=150, width=580)
        self.news_frame.pack_propagate(False)
        self.news_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(self.news_frame, text="Latest News", font=("Arial", 12, "bold")).pack()
        self.news_label = HTMLLabel(self.news_frame, html=self.fetch_news())
        self.news_label.pack(fill="both", expand=True, padx=5, pady=5)

    def create_bottom_section(self):
        """Creates the bottom section for Download button, progress bar, and status."""
        self.bottom_frame = tk.Frame(self)
        self.bottom_frame.pack(fill="x", padx=10, pady=10)

        # Status Label
        self.status_label = tk.Label(self.bottom_frame, text="Checking mod status...", fg="blue")
        self.status_label.pack(pady=5)

        # Download Button
        self.download_button = tk.Button(
            self.bottom_frame, text="Checking...", state="disabled", command=self.download_and_extract_mod
        )
        self.download_button.pack(pady=5)
        # Tooltip(self.download_button, "Download and install the latest version of the mod.")

        # Progress Bar
        self.progress = ttk.Progressbar(self.bottom_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)
        self.progress.pack_forget()

        # Folder Path Display
        self.folder_label = tk.Label(
            self, text="Installation Folder: Not selected", font=("Arial", 10), anchor="w", justify="left"
        )
        self.folder_label.pack(fill="x", side="bottom", padx=10, pady=5)

    def fetch_news(self):
        """Fetches the news content."""
        try:
            response = requests.get(f"{NEWS_URL}?t={int(time.time())}")
            if response.status_code == 200:
                return response.text
            return "<p>Failed to fetch news.</p>"
        except Exception as e:
            return f"<p>Error: {e}</p>"

    def load_last_folder(self):
        """Loads the last selected folder and mod state from the registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                folder, _ = winreg.QueryValueEx(key, "InstallFolder")
                installed, _ = winreg.QueryValueEx(key, "Installed")

            if os.path.exists(folder):
                if installed:  # Mod installed
                    self.install_folder.set(folder)
                    self.is_installed = True
                    self.folder_label.config(text=f"Installation Folder: {folder}")
                    self.check_for_mod_updates()
                else:  # Folder exists, but mod not installed
                    self.reset_folder()
            else:
                self.reset_folder()
        except FileNotFoundError:
            self.reset_folder()

    def reset_folder(self):
        """Resets the folder selection and clears registry data."""
        self.install_folder.set("")
        self.is_installed = False
        self.status_label.config(text="No folder saved. Please select an installation folder.", fg="red")
        self.folder_label.config(text="Installation Folder: Not selected")  # Reset the label
        self.hide_download_button()
        self.uninstall_button.config(state="disabled")  # Disable the Uninstall button instead of hiding

    def select_folder(self):
        """Opens dialog to select folder and checks mod updates."""
        folder = filedialog.askdirectory()
        if folder:
            self.install_folder.set(folder)
            self.folder_label.config(text=f"Installation Folder: {folder}")  # Update the label
            self.save_folder(folder, installed=False)
            self.status_label.config(text="Checking mod status...", fg="blue")
            self.check_for_mod_updates()
        else:
            self.status_label.config(text="Please select an installation folder.", fg="red")
            self.hide_download_button()

    def save_folder(self, folder, installed):
        """Saves the folder path and installation state to the registry."""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                winreg.SetValueEx(key, "InstallFolder", 0, winreg.REG_SZ, folder)
                winreg.SetValueEx(key, "Installed", 0, winreg.REG_DWORD, int(installed))
        except Exception as e:
            print(f"Error saving to registry: {e}")

    def check_for_mod_updates(self):
        """Checks for mod updates and updates the UI."""
        install_path = self.install_folder.get()
        version_file = os.path.join(install_path, "realms_version.json")

        # Check local version
        local_version = "not installed"
        if os.path.exists(version_file):
            try:
                with open(version_file, "r") as file:
                    content = file.read().strip()
                    if content:  # Ensure the file is not empty
                        local_version = json.loads(content).get("version", "unknown")
                    self.is_installed = True
            except (json.JSONDecodeError, ValueError):
                local_version = "unknown"
                self.is_installed = False

        # Compare with remote version
        try:
            response = requests.get(f"{MOD_INFO_URL}?t={int(time.time())}")
            if response.status_code == 200:
                remote_version = response.json().get("version", "0.0.0")

                if local_version == "not installed":
                    self.status_label.config(text="No mod found. Ready to download.", fg="green")
                    self.download_button.config(text="Download Mod", state="normal")
                    self.show_download_button()
                    self.uninstall_button.config(state="disabled")  # Disable Uninstall button
                    self.create_shortcut_button.config(state="disabled")  # Disable Shortcut button
                    self.folder_button.config(state="normal")  # Enable Select Folder button
                elif local_version != remote_version:
                    self.status_label.config(
                        text=f"Update available: {remote_version} (Installed: {local_version})", fg="orange"
                    )
                    self.download_button.config(text="Download Update", state="normal")
                    self.show_download_button()
                    self.uninstall_button.config(state="normal")  # Enable Uninstall button
                    self.create_shortcut_button.config(state="normal")  # Enable Shortcut button
                    self.folder_button.config(state="disabled")  # Disable Select Folder button
                else:
                    self.status_label.config(text=f"Mod is up-to-date ({local_version}).", fg="green")
                    self.hide_download_button()  # Hide the download button
                    self.uninstall_button.config(state="normal")  # Ensure Uninstall button is enabled
                    self.create_shortcut_button.config(state="normal")  # Enable Shortcut button
                    self.folder_button.config(state="disabled")  # Disable Select Folder button
            else:
                self.status_label.config(text="Failed to check for updates.", fg="red")
                self.download_button.config(text="Retry", state="normal")
                self.show_download_button()
                self.uninstall_button.config(state="disabled")  # Disable Uninstall button
                self.create_shortcut_button.config(state="disabled")  # Disable Shortcut button

        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.download_button.config(text="Retry", state="normal")
            self.show_download_button()
            self.uninstall_button.config(state="disabled")  # Disable Uninstall button
            self.create_shortcut_button.config(state="disabled")  # Disable Shortcut button

    def show_download_button(self):
        """Show the download button."""
        self.download_button.pack(pady=5)

    def hide_download_button(self):
        """Hide the download button."""
        self.download_button.pack_forget()

    def download_and_extract_mod(self):
        """Downloads and installs the mod."""
        install_path = self.install_folder.get()
        if not install_path:
            self.status_label.config(text="No installation folder selected.", fg="red")
            return

        try:
            # Hide the Download button during the download process
            self.hide_download_button()
            self.progress.pack()  # Show progress bar
            self.status_label.config(text="Downloading...", fg="blue")
            self.update()

            # Download the ZIP file
            zip_path = os.path.join(install_path, "mod.zip")
            response = requests.get(MOD_ZIP_URL, stream=True)
            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            with open(zip_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        self.progress["value"] = (downloaded_size / total_size) * 100
                        self.update()

            self.status_label.config(text="Installing...", fg="blue")
            self.update()

            # Extract the ZIP file
            with ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(install_path)

            os.remove(zip_path)  # Remove the downloaded ZIP file

            # Save the installed version
            version_file = os.path.join(install_path, "realms_version.json")
            with open(version_file, "w") as file:
                json.dump({"version": self.get_remote_version()}, file)

            # Update status and enable uninstall button
            self.status_label.config(text="Mod installed successfully!", fg="green")
            self.uninstall_button.config(state="normal")  # Enable the Uninstall button
            self.progress.pack_forget()  # Hide progress bar
            self.save_folder(install_path, installed=True)

            # Automatically create a shortcut
            self.create_shortcut()

            # Update UI after installation
            self.check_for_mod_updates()  # Force an update of the UI

        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.progress.pack_forget()  # Hide progress bar
            self.show_download_button()  # Show the Download button again if there's an error

    def get_remote_version(self):
        """Fetches the remote mod version."""
        try:
            response = requests.get(MOD_INFO_URL)
            if response.status_code == 200:
                return response.json().get("version", "0.0.0")
        except Exception as e:
            print(f"Error fetching remote version: {e}")
        return "0.0.0"

    def uninstall_mod(self):
        """Uninstalls the mod and removes all folders, subfolders, and shortcuts."""
        folder = self.install_folder.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "No valid installation folder selected.")
            return

        if messagebox.askyesno(
            "Confirm Uninstall",
            "Do you really want to uninstall the mod? This will delete all files and folders in the selected directory."
        ):
            try:
                # Use shutil.rmtree to delete the folder and all its contents
                shutil.rmtree(folder)

                # Locate the shortcut and delete it
                desktop = os.path.normpath(os.path.join(os.environ["USERPROFILE"], "Desktop"))
                shortcut_pattern = "Realms in Exile v*.lnk"  # Pattern for the shortcut name

                for file in os.listdir(desktop):
                    if re.match(rf"Realms in Exile v.*\.lnk", file):  # Match all versions
                        shortcut_path = os.path.join(desktop, file)
                        os.remove(shortcut_path)  # Delete the shortcut
                        print(f"Deleted shortcut: {shortcut_path}")

                # Reset UI and clear registry
                self.status_label.config(
                    text="Mod uninstalled successfully. All files and folders were removed.", fg="green"
                )
                self.folder_label.config(text="Installation Folder: Not selected")
                self.install_folder.set("")
                self.save_folder("", installed=False)

                # Update UI elements
                self.hide_download_button()  # Ensure the Download button is hidden
                self.uninstall_button.config(state="disabled")  # Disable the Uninstall button (no hiding)
                self.create_shortcut_button.config(state="disabled")  # Disable the Shortcut button
                self.folder_button.config(state="normal")  # Enable the Select Folder button

            except Exception as e:
                self.status_label.config(text=f"Error uninstalling mod: {e}", fg="red")
                print(f"Error during uninstallation: {e}")

    def create_shortcut(self):
        """Creates a shortcut to launch the mod with the appropriate parameters."""
        try:
            # Locate the game executable from the registry
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Electronic Arts\Electronic Arts\The Lord of the Rings, The Rise of the Witch-king") as key:
                game_install_path, _ = winreg.QueryValueEx(key, "InstallPath")

            game_executable = os.path.normpath(os.path.join(game_install_path, "lotrbfme2ep1.exe"))
            if not os.path.exists(game_executable):
                messagebox.showerror("Error", "Could not find the game executable.")
                return

            # Get the mod folder and verify the icon file
            mod_folder = os.path.normpath(self.install_folder.get())
            icon_path = os.path.normpath(os.path.join(mod_folder, "aotr_fs.ico"))
            if not os.path.exists(icon_path):
                messagebox.showerror("Error", "Icon file 'aotr_fs.ico' not found in the mod folder.")
                return

            # Get the mod version
            version_file = os.path.join(mod_folder, "realms_version.json")
            if os.path.exists(version_file):
                with open(version_file, "r") as file:
                    mod_version = json.load(file).get("version", "unknown")
            else:
                mod_version = "unknown"

            # Create the shortcut name
            desktop = os.path.normpath(os.path.join(os.environ["USERPROFILE"], "Desktop"))
            shortcut_name = f"Realms in Exile v{mod_version}.lnk"
            shortcut_path = os.path.join(desktop, shortcut_name)

            # Add the mod parameter
            arguments = f'-mod "{mod_folder}"'

            # Create the shortcut
            import winshell
            with winshell.shortcut(shortcut_path) as shortcut:
                shortcut.path = game_executable
                shortcut.arguments = arguments
                shortcut.description = f"Launch Realms in Exile v{mod_version}"
                shortcut.icon_location = (icon_path, 0)  # Use the icon from the mod folder

            messagebox.showinfo("Shortcut Created", f"Shortcut created on the desktop: {shortcut_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create shortcut: {e}")

if __name__ == "__main__":
    app = ModLauncher()
    app.mainloop()