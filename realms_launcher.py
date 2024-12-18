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

# Constants
MOD_INFO_URL = "https://storage.googleapis.com/realms-in-exile/updater/version.json"                # URL to check the mod version (JSON format)
MOD_ZIP_URL = "https://storage.googleapis.com/realms-in-exile/updater/realms_beta.zip"              # URL to download the mod
NEWS_URL = "https://raw.githubusercontent.com/hansnery/Realms-Launcher/refs/heads/main/news.html"   # URL for news content
LAUNCHER_VERSION = "1.0.0"
LAUNCHER_VERSION_URL = "https://storage.googleapis.com/realms-in-exile/updater/launcher_version.json"
LAUNCHER_UPDATE_URL = "https://storage.googleapis.com/realms-in-exile/updater/launcher_update.zip"
REG_PATH = r"SOFTWARE\REALMS_Launcher"

class ModLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Age of the Ring: Realms in Exile Launcher")
        self.geometry("600x500")
        self.resizable(False, False)
        self.iconbitmap("aotr_fs.ico")

        # Selected folder for installation
        self.install_folder = tk.StringVar()
        self.version_info = tk.StringVar(value="Checking for updates...")

        # UI Components
        self.create_banner()
        self.create_buttons()
        self.create_main_area()

        # Load last folder and check mod version if a folder is saved
        self.after(100, self.load_last_folder)  # Ensure it starts after the UI is initialized

        # Check for launcher updates
        self.check_for_launcher_updates()

    def create_main_area(self):
        """Creates a single-column layout for the news, download button, and status message."""
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Dynamic Button (Above Status Message)
        self.download_button = tk.Button(
            main_frame,
            text="Checking...",
            state="disabled",
            command=self.download_and_extract_mod,
            font=("Arial", 10)
        )
        self.download_button.pack(pady=5)

        # Status Label
        self.status_label = tk.Label(
            main_frame,
            text="Checking mod status...",
            font=("Arial", 10),
            fg="blue",
            anchor="center"
        )
        self.status_label.pack(pady=5)

        # Progress Bar (Below Status Label)
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)
        self.progress.pack_forget()  # Initially hidden

        # News Section
        news_frame = tk.Frame(main_frame, borderwidth=2, relief="groove", height=150, width=580)
        news_frame.pack_propagate(False)  # Prevent resizing
        news_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(news_frame, text="Latest News", font=("Arial", 12, "bold")).pack()
        self.news_label = HTMLLabel(news_frame, html=self.fetch_news())
        self.news_label.pack(fill="both", expand=True, padx=5, pady=5)

        # Installation Folder Display (Below All)
        self.folder_display = tk.Label(
            main_frame,
            text="Installation Folder: Not selected",
            font=("Arial", 10),
            anchor="w",
            justify="left"
        )
        self.folder_display.pack(fill="x", padx=10, pady=5)
        
    def create_banner(self):
        """Displays a banner image at the top."""
        try:
            image = Image.open("banner.png")  # Place banner.png in the same folder
            image = image.resize((600, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            banner = tk.Label(self, image=photo)
            banner.image = photo
            banner.pack()
        except Exception as e:
            self.version_info.set(f"Image Error: {e}")
        
    def fetch_news(self):
        """Fetch plain news content from the server."""
        try:
            response = requests.get(f"{NEWS_URL}?t={int(time.time())}")
            if response.status_code == 200:
                return response.text  # Return the raw HTML content
            else:
                return "<p>Failed to fetch news. Please try again later.</p>"
        except Exception as e:
            return f"<p>Error: {e}</p>"
        
    def check_for_launcher_updates(self):
        """Checks for launcher updates and auto-updates if necessary."""
        try:
            response = requests.get(f"{LAUNCHER_VERSION_URL}?t={int(time.time())}")
            if response.status_code == 200:
                launcher_info = response.json()
                latest_version = launcher_info.get("version", "0.0.0")
                changelog = launcher_info.get("changelog", "No changelog available.")
                update_url = launcher_info.get("update_url")

                if LAUNCHER_VERSION != latest_version:
                    self.version_info.set(f"New launcher version {latest_version} available.\nChangelog: {changelog}. Updating...")
                    self.download_and_update_launcher(update_url)
                else:
                    self.version_info.set("Launcher is up-to-date.")
        except Exception as e:
            self.version_info.set(f"Error checking for launcher update: {e}")
        
    def load_last_folder(self):
        """Loads the last selected folder from the Windows Registry and checks for mod updates."""
        try:
            # Open the Windows Registry to retrieve the saved folder
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                folder, _ = winreg.QueryValueEx(key, "InstallFolder")

            # Ensure the folder exists on the filesystem
            if os.path.exists(folder):
                self.install_folder.set(folder)  # Set the folder path
                self.folder_display.config(text=f"Installation Folder: {folder}")
                print(f"Loaded folder from registry: {folder}")  # Debugging log
                self.check_for_mod_updates()  # Check for mod updates immediately
            else:
                # If the folder doesn't exist, prompt the user to select a new one
                self.status_label.config(text="Saved folder not found. Please select a new folder.", fg="red")
                self.folder_display.config(text="Installation Folder: Not selected")
                self.hide_download_button()
        except FileNotFoundError:
            # Handle the case where no folder is saved in the registry
            self.status_label.config(text="No folder saved. Please select an installation folder.", fg="red")
            self.folder_display.config(text="Installation Folder: Not selected")
            self.hide_download_button()
        except Exception as e:
            # Handle other exceptions gracefully
            print(f"Error loading folder from registry: {e}")
            self.status_label.config(text="Error loading folder. Please select an installation folder.", fg="red")
            self.folder_display.config(text="Installation Folder: Not selected")
            self.hide_download_button()

    def show_download_button(self):
        """Show the download button below the folder button."""
        self.download_button.pack(side="top", pady=5)

    def hide_download_button(self):
        """Hide the download button."""
        self.download_button.pack_forget()

    def save_last_folder(self, folder):
        """Saves the selected folder path to the Windows Registry."""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
            winreg.SetValueEx(key, "InstallFolder", 0, winreg.REG_SZ, folder)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Error saving folder to registry: {e}")

    def create_buttons(self):
        """Creates the button frame for 'Select Install Folder' and 'Download Mod'."""
        self.button_frame = tk.Frame(self)
        self.button_frame.pack(pady=10)

        # Folder Selection Button
        self.folder_button = tk.Button(self.button_frame, text="Select Install Folder", command=self.select_folder)
        self.folder_button.pack(side="top", pady=5)

        # Download Mod Button (initially hidden)
        self.download_button = tk.Button(
            self.button_frame,
            text="Checking...",
            state="disabled",
            command=self.download_and_extract_mod,
            font=("Arial", 10)
        )
        self.download_button.pack(side="top", pady=5)
        self.download_button.pack_forget()  # Hidden by default

    def select_folder(self):
        """Opens a dialog to select the mod installation folder and checks for existing mod version."""
        folder = filedialog.askdirectory()
        if folder:
            self.install_folder.set(folder)
            self.folder_display.config(text=f"Installation Folder: {folder}")
            self.status_label.config(text="Checking mod status...", fg="blue")  # Reset status message
            self.save_last_folder(folder)
            self.show_download_button()  # Show the button when a folder is selected
            self.check_for_mod_updates()  # Check mod updates after folder selection
        else:
            self.status_label.config(text="Please select an installation folder", fg="red")
            self.hide_download_button()
    
    def check_for_mod_updates(self):
        """Checks the current mod version from realms_version.json and updates the UI."""
        install_path = self.install_folder.get()
        if not install_path:
            self.status_label.config(text="Please select an install folder first.", fg="red")
            self.download_button.config(text="Select Folder", state="disabled")
            return

        try:
            # Check the latest mod version from the server
            self.status_label.config(text="Checking mod status...", fg="blue")
            self.download_button.config(text="Checking...", state="disabled")
            self.update()

            response = requests.get(f"{MOD_INFO_URL}?t={int(time.time())}")
            if response.status_code == 200:
                mod_info = response.json()
                latest_version = mod_info.get("version", "0.0.0")
                local_version = self.get_local_version(install_path)

                if local_version == "not installed":
                    self.status_label.config(text="No mod found. Ready to download.", fg="green")
                    self.download_button.config(text="Download Mod", state="normal")
                    self.folder_button.config(text="Select Install Folder", command=self.select_folder)
                elif local_version != latest_version:
                    self.status_label.config(
                        text=f"New version {latest_version} available! (Installed: {local_version})", fg="orange"
                    )
                    self.download_button.config(text="Download Update", state="normal")
                    self.folder_button.config(text="Uninstall Mod", command=self.uninstall_mod)
                else:
                    self.status_label.config(text="Mod is up-to-date.", fg="green")
                    self.download_button.pack_forget()  # Hide the download button
                    self.folder_button.config(text="Uninstall Mod", command=self.uninstall_mod)
            else:
                self.status_label.config(text="Failed to check mod version. Please try again.", fg="red")
                self.download_button.config(text="Retry", state="normal")

        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.download_button.config(text="Retry", state="normal")

        self.update()

    def get_local_version(self, install_path):
        """Reads the local mod version from realms_version.json or returns 'not installed'."""
        version_file = os.path.join(install_path, "realms_version.json")
        if os.path.exists(version_file):
            try:
                with open(version_file, "r") as file:
                    data = json.load(file)
                    return data.get("version", "unknown")
            except (json.JSONDecodeError, KeyError):
                return "unknown"
        return "not installed"

    def download_and_extract_mod(self):
        """Downloads and extracts the mod to the selected folder with progress updates."""
        install_path = self.install_folder.get()
        if not install_path:
            self.status_label.config(text="Please select an installation folder first.", fg="red")
            return

        try:
            # Show the progress bar
            self.progress.pack()
            self.status_label.config(text="Downloading...", fg="blue")  # Set status to 'Downloading'
            self.update()

            # Download the ZIP file with progress
            response = requests.get(MOD_ZIP_URL, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            zip_path = os.path.join(install_path, "mod.zip")

            self.progress["value"] = 0
            self.progress["maximum"] = total_size

            with open(zip_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        self.progress["value"] = downloaded_size
                        self.update()

            self.status_label.config(text="Installing...", fg="blue")  # Set status to 'Installing'
            self.update()

            # Extract the ZIP file with progress
            with ZipFile(zip_path, "r") as zip_ref:
                file_count = len(zip_ref.namelist())
                extracted_files = 0

                for file in zip_ref.namelist():
                    zip_ref.extract(file, install_path)
                    extracted_files += 1
                    self.progress["value"] = extracted_files / file_count * 100 * total_size / 100
                    self.update()

            os.remove(zip_path)
            self.write_mod_version(install_path)

            self.status_label.config(text="Mod installed successfully!", fg="green")

            # Hide the buttons after successful installation
            self.download_button.pack_forget()
            for widget in self.winfo_children():
                if isinstance(widget, tk.Button) and widget.cget("text") == "Select Install Folder":
                    widget.pack_forget()

        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
        finally:
            self.progress.pack_forget()  # Hide the progress bar
            self.progress["value"] = 0
            self.update()

    def write_mod_version(self, install_path):
      """Writes the current mod version to realms_version.json."""
      try:
          response = requests.get(f"{MOD_INFO_URL}?t={int(time.time())}")
          if response.status_code == 200:
              mod_info = response.json()
              latest_version = mod_info.get("version", "0.0.0")

              # Write the version to realms_version.json
              version_file_path = os.path.join(install_path, "realms_version.json")
              with open(version_file_path, "w") as version_file:
                  json.dump({"version": latest_version}, version_file, indent=4)

              self.version_info.set("Mod version saved successfully.")
          else:
              self.version_info.set("Failed to fetch mod version for saving.")
      except Exception as e:
          self.version_info.set(f"Error writing mod version: {e}")

    def uninstall_mod(self):
        """Deletes the mod files and resets the UI."""
        install_path = self.install_folder.get()
        if not install_path:
            messagebox.showerror("Error", "No installation folder selected.")
            return

        confirm = messagebox.askyesno("Uninstall Mod", "Are you sure you want to uninstall the mod?")
        if confirm:
            try:
                # Delete the realms_version.json file
                version_file = os.path.join(install_path, "realms_version.json")
                if os.path.exists(version_file):
                    os.remove(version_file)

                # Optionally delete all files in the installation folder
                for root, dirs, files in os.walk(install_path, topdown=False):
                    for file in files:
                        os.remove(os.path.join(root, file))
                    for dir in dirs:
                        os.rmdir(os.path.join(root, dir))

                self.status_label.config(text="Mod uninstalled successfully.", fg="green")
                self.folder_display.config(text="Installation Folder: Not selected")
                self.folder_button.config(text="Select Install Folder", command=self.select_folder)
                self.download_button.config(text="Download Mod", state="normal")

            except Exception as e:
                self.status_label.config(text=f"Error uninstalling mod: {e}", fg="red")

if __name__ == "__main__":
    app = ModLauncher()
    app.mainloop()