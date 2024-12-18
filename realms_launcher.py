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
MOD_INFO_URL = "https://storage.googleapis.com/realms-in-exile/updater/version.json"    # URL to check the mod version (JSON format)
MOD_ZIP_URL = "https://storage.googleapis.com/realms-in-exile/updater/realms_beta.zip"  # URL to download the mod
NEWS_URL = "https://storage.googleapis.com/realms-in-exile/updater/news.html"           # URL for news content
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
        self.create_news_area()
        self.create_buttons()
        self.create_status_area()

        # Load last folder and check mod version if a folder is saved
        self.after(100, self.load_last_folder)  # Ensure it starts after the UI is initialized

        # Check for launcher updates
        self.check_for_launcher_updates()
        
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

    def create_news_area(self):
        """Creates a news area using HTMLLabel for lightweight HTML rendering."""
        news_frame = tk.Frame(self, borderwidth=2, relief="groove", height=200)
        news_frame.pack_propagate(False)  # Prevent the frame from expanding
        news_frame.pack(padx=10, pady=10, fill="x")

        # Title
        tk.Label(news_frame, text="Latest News", font=("Arial", 14, "bold")).pack()

        # HTML news content
        self.news_label = HTMLLabel(news_frame, html=self.fetch_news())
        self.news_label.pack(fill="both", expand=True, padx=5, pady=5)
        
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
            # Open Registry and read the folder path
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
            folder, _ = winreg.QueryValueEx(key, "InstallFolder")
            winreg.CloseKey(key)
            
            # Verify the folder exists
            if os.path.exists(folder):
                self.install_folder.set(folder)  # Set the folder path
                self.version_info.set(f"Folder loaded: {folder}. Checking mod version...")
                self.after(100, self.check_for_mod_updates)  # Delay to allow the UI to update
            else:
                self.version_info.set("Saved folder not found. Please select a new folder.")
        except FileNotFoundError:
            self.version_info.set("No folder saved. Please select an install folder.")
        except Exception as e:
            print(f"Error loading folder from registry: {e}")
            self.version_info.set("Error loading last folder. Please select a new folder.")

    def save_last_folder(self, folder):
        """Saves the selected folder path to the Windows Registry."""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
            winreg.SetValueEx(key, "InstallFolder", 0, winreg.REG_SZ, folder)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Error saving folder to registry: {e}")

    def create_buttons(self):
        """Adds buttons for selecting folder and updating."""
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        # Folder Selection Button
        tk.Button(button_frame, text="Select Install Folder", command=self.select_folder).pack(side="left", padx=5)
        # Download Mod Button
        tk.Button(button_frame, text="Download Mod", command=self.download_and_extract_mod).pack(side="left", padx=5)
        # Exit Button
        # tk.Button(button_frame, text="Exit", command=self.quit).pack(side="left", padx=5)

    def create_status_area(self):
        """Adds a status label for version information."""
        self.status_label = tk.Label(self, textvariable=self.version_info, font=("Arial", 10))
        self.status_label.pack(pady=10)

    def select_folder(self):
        """Opens a dialog to select the mod installation folder and checks for existing mod version."""
        folder = filedialog.askdirectory()
        if folder:
            self.install_folder.set(folder)
            self.save_last_folder(folder)  # Save the folder
            version = self.get_local_version()

            if version == "not installed":
                self.version_info.set(f"No mod found in the selected folder: {folder}. Ready to install.")
            else:
                self.version_info.set(f"Mod found in folder: {folder}. Installed version: {version}")
                self.check_for_mod_updates()
    
    def check_for_mod_updates(self):
        """Checks the current mod version and notifies if updates are available."""
        if not self.install_folder.get():
            self.version_info.set("Please select an install folder first.")
            return

        try:
            self.version_info.set("Checking mod version...")
            response = requests.get(f"{MOD_INFO_URL}?t={int(time.time())}")
            if response.status_code == 200:
                mod_info = response.json()
                latest_version = mod_info.get("version", "0.0.0")
                changelog = mod_info.get("changelog", "No changelog available.")
                local_version = self.get_local_version()

                if local_version != latest_version:
                    self.version_info.set(
                        f"New mod version {latest_version} available.\n{changelog}\n"
                        f"Located in: {self.install_folder.get()}\n"
                        "Click 'Download Mod' to install the update."
                    )
                else:
                    self.version_info.set(
                        f"Mod is already up-to-date.\nLocated in: {self.install_folder.get()}"
                    )
            else:
                self.version_info.set("Failed to check mod version.")
        except Exception as e:
            self.version_info.set(f"Error checking mod version: {e}")

    def get_local_version(self):
        """Reads the local mod version from realms_version.json or returns 'not installed'."""
        version_file = os.path.join(self.install_folder.get(), "realms_version.json")
        if os.path.exists(version_file):
            try:
                with open(version_file, "r") as file:
                    data = json.load(file)
                    return data.get("version", "not installed")
            except Exception:
                return "not installed"
        return "not installed"

    def download_and_extract_mod(self):
      """Downloads and extracts the mod to the selected folder with a progress bar and writes version info."""
      install_path = self.install_folder.get()
      if not install_path:
          self.version_info.set("Please select an install folder first.")
          return

      try:
          # Show the progress bar
          self.progress.pack()
          self.version_info.set("Downloading mod...")
          self.update()

          response = requests.get(MOD_ZIP_URL, stream=True)
          total_size = int(response.headers.get('content-length', 0))  # Total size of the file
          downloaded_size = 0
          zip_path = os.path.join(install_path, "mod.zip")

          # Initialize progress bar
          self.progress["value"] = 0
          self.progress["maximum"] = total_size

          # Save the zip file with progress updates
          with open(zip_path, "wb") as file:
              for chunk in response.iter_content(chunk_size=1024):
                  if chunk:
                      file.write(chunk)
                      downloaded_size += len(chunk)
                      self.progress["value"] = downloaded_size
                      self.update()

          self.version_info.set("Download complete. Extracting files...")
          self.update()

          # Extract the mod
          with ZipFile(zip_path, "r") as zip_ref:
              file_count = len(zip_ref.namelist())
              extracted_files = 0

              for file in zip_ref.namelist():
                  zip_ref.extract(file, install_path)
                  extracted_files += 1
                  self.progress["value"] = extracted_files / file_count * 100
                  self.update()

          os.remove(zip_path)

          # Write version file
          self.write_mod_version(install_path)

          self.version_info.set("Mod installed successfully!")
      except Exception as e:
          self.version_info.set(f"Failed to download or extract mod: {e}")
      finally:
          # Hide the progress bar
          self.progress.pack_forget()
          self.progress["value"] = 0  # Reset progress
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

    def create_status_area(self):
      """Adds a status label and a hidden progress bar for version information."""
      status_frame = tk.Frame(self)
      status_frame.pack(pady=10, fill="x")

      # Status label
      self.status_label = tk.Label(status_frame, textvariable=self.version_info, font=("Arial", 10))
      self.status_label.pack(pady=5)

      # Progress bar (hidden initially)
      self.progress = ttk.Progressbar(status_frame, orient="horizontal", length=400, mode="determinate")
      self.progress.pack(pady=5)
      self.progress.pack_forget()  # Hide initially

if __name__ == "__main__":
    app = ModLauncher()
    app.mainloop()
