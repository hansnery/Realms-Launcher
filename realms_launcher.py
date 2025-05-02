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
import tempfile
import subprocess  # Import subprocess for launching the game

# Constants
MOD_INFO_URL = "https://realmsinexile.s3.us-east-005.backblazeb2.com/version.json"
BASE_MOD_VERSION = "0.7.3"  # Base version of the mod
BASE_MOD_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_beta.zip"  # Base mod download
UPDATE_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_update.zip"  # Update package
LAUNCHER_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_launcher.zip"  # Launcher update package
NEWS_URL = "https://raw.githubusercontent.com/hansnery/Realms-Launcher/refs/heads/main/news.html"
LAUNCHER_VERSION = "1.0.3"  # Updated launcher version
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
        self.geometry("600x520")
        self.resizable(False, False)
        self.iconbitmap(self.resource_path("aotr_fs.ico"))

        # Selected folder and mod state
        self.install_folder = tk.StringVar()
        self.is_installed = False
        
        # Language selection
        self.language = tk.StringVar()
        self.language.set("english")  # Default language

        # Layout Frames
        self.create_banner()
        self.create_top_buttons()
        self.create_news_section()
        self.create_bottom_section()

        # Load last folder and check mod version
        self.after(100, self.load_last_folder)

        # Check for updates for the launcher
        self.check_launcher_update()

    def resource_path(self, relative_path):
        """Get the absolute path to the resource, works for both dev and PyInstaller."""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def create_banner(self):
        """Displays the banner at the top."""
        try:
            image = Image.open(self.resource_path("banner.png"))
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
        # self.create_shortcut_button.pack(side="left", padx=10, pady=5)
        # Tooltip(self.create_shortcut_button, "Create a desktop shortcut to launch the mod.")
        
        # Language dropdown
        language_frame = tk.Frame(self.top_frame)
        language_frame.pack(side="left", padx=10, pady=5)
        
        language_label = tk.Label(language_frame, text="Language:")
        language_label.pack(side="left")
        
        self.language_dropdown = ttk.Combobox(language_frame, textvariable=self.language, state="readonly", width=15)
        self.language_dropdown["values"] = ["English", "Portuguese (BR)"]
        self.language_dropdown.current(0)  # Set default to English
        self.language_dropdown.pack(side="left", padx=5)
        self.language_dropdown.bind("<<ComboboxSelected>>", self.change_language)
        Tooltip(self.language_dropdown, "Change the language of the mod.")

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

        # Button frame for Play and Download buttons
        self.button_frame = tk.Frame(self.bottom_frame)
        self.button_frame.pack(pady=5)
        
        # Play Button (initially hidden)
        self.play_button = tk.Button(
            self.button_frame,
            text="Play Mod",
            #bg="green",
            # fg="white",
            font=("Arial", 10, "bold"),
            width=15,
            height=2,
            command=self.launch_game
        )
        
        # Download Button
        self.download_button = tk.Button(
            self.button_frame,
            text="Checking...",
            state="disabled",
            bg="green",
            fg="white",
            font=("Arial", 10, "bold"),
            width=15,
            height=2,
            command=self.download_and_extract_mod
        )
        self.download_button.pack(side="left", padx=5)

        # Progress Bar
        self.progress = ttk.Progressbar(self.bottom_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)
        self.progress.pack_forget()

        # Bottom info frame (folder path on the left, version on the right)
        self.bottom_info_frame = tk.Frame(self)
        self.bottom_info_frame.pack(side="bottom", fill="x", padx=10, pady=10)  # Increase pady from 5 to 10

        # Folder Label (left)
        self.folder_label = tk.Label(
            self.bottom_info_frame,
            text="Installation Folder: Not selected",
            font=("Arial", 10),
            anchor="w",
            height=2  # Add this line to give more vertical space
        )
        self.folder_label.pack(side="left", fill="x", expand=True)  # Add fill and expand

        # Launcher Version Label (right)
        self.version_label = tk.Label(
            self.bottom_info_frame,
            text=f"Launcher v{LAUNCHER_VERSION}",
            font=("Arial", 10),
            anchor="e",
            height=2  # Match the height with folder_label
        )
        self.version_label.pack(side="right", padx=(10, 0))  # Add some padding between labels

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
                
                # Try to load language setting if it exists
                try:
                    lang, _ = winreg.QueryValueEx(key, "Language")
                    self.language.set(lang)
                    if lang.lower() == "english":
                        self.language_dropdown.current(0)
                    elif lang.lower() == "portuguese (br)":
                        self.language_dropdown.current(1)
                except:
                    # If language setting doesn't exist, default to English
                    self.language.set("English")
                    self.language_dropdown.current(0)

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
        self.hide_play_button()  # Hide play button
        self.uninstall_button.config(state="disabled")  # Disable the Uninstall button instead of hiding
        self.create_shortcut_button.config(state="disabled")  # Disable the Shortcut button
        self.language_dropdown.config(state="disabled")  # Disable the language dropdown

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
            self.hide_play_button()  # Hide play button

    def save_folder(self, folder, installed):
        """Saves the folder path and installation state to the registry."""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                winreg.SetValueEx(key, "InstallFolder", 0, winreg.REG_SZ, folder)
                winreg.SetValueEx(key, "Installed", 0, winreg.REG_DWORD, int(installed))
                winreg.SetValueEx(key, "Language", 0, winreg.REG_SZ, self.language.get())
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
                    self.status_label.config(text=f"No mod found. Ready to download base version {BASE_MOD_VERSION}.", fg="green")
                    self.download_button.config(text="Download Base Mod", state="normal")
                    self.show_download_button()
                    self.hide_play_button()  # Hide play button
                    self.uninstall_button.config(state="disabled")  # Disable Uninstall button
                    # self.create_shortcut_button.config(state="disabled")  # Disable Shortcut button
                    self.folder_button.config(state="normal")  # Enable Select Folder button
                    self.language_dropdown.config(state="disabled")  # Disable language dropdown
                elif local_version != remote_version:
                    self.status_label.config(
                        text=f"Update available: {remote_version} (Installed: {local_version})", fg="orange"
                    )
                    self.download_button.config(text="Download Update", state="normal")
                    self.show_download_button()
                    self.show_play_button()  # Show play button for current version
                    self.uninstall_button.config(state="normal")  # Enable Uninstall button
                    self.create_shortcut_button.config(state="normal")  # Enable Shortcut button
                    self.folder_button.config(state="disabled")  # Disable Select Folder button
                    self.language_dropdown.config(state="readonly")  # Enable language dropdown
                else:
                    self.status_label.config(text=f"Mod is up-to-date ({local_version}).", fg="green")
                    self.hide_download_button()  # Hide the download button
                    self.show_play_button()  # Show play button
                    self.uninstall_button.config(state="normal")  # Ensure Uninstall button is enabled
                    self.create_shortcut_button.config(state="normal")  # Enable Shortcut button
                    self.folder_button.config(state="disabled")  # Disable Select Folder button
                    self.language_dropdown.config(state="readonly")  # Enable language dropdown
            else:
                self.status_label.config(text="Failed to check for updates.", fg="red")
                self.download_button.config(text="Retry", state="normal")
                self.show_download_button()
                self.hide_play_button()  # Hide play button on error
                self.uninstall_button.config(state="disabled")  # Disable Uninstall button
                self.create_shortcut_button.config(state="disabled")  # Disable Shortcut button
                self.language_dropdown.config(state="disabled")  # Disable language dropdown

        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.download_button.config(text="Retry", state="normal")
            self.show_download_button()
            self.hide_play_button()  # Hide play button on error
            self.uninstall_button.config(state="disabled")  # Disable Uninstall button
            self.create_shortcut_button.config(state="disabled")  # Disable Shortcut button
            self.language_dropdown.config(state="disabled")  # Disable language dropdown

    def show_download_button(self):
        """Show the download button."""
        self.download_button.pack(side="left", padx=5)

    def hide_download_button(self):
        """Hide the download button."""
        self.download_button.pack_forget()
        
    def show_play_button(self):
        """Show the play button."""
        self.play_button.pack(side="left", padx=5)
        
    def hide_play_button(self):
        """Hide the play button."""
        self.play_button.pack_forget()
        
    def change_language(self, event=None):
        """Change the language of the mod."""
        if not self.is_installed:
            return
            
        install_path = self.install_folder.get()
        if not install_path:
            messagebox.showerror("Error", "No installation folder selected.")
            return
            
        # Data folder path
        data_folder = os.path.join(install_path, "data")
        translations_folder = os.path.join(data_folder, "translations")
        
        # Target file
        target_file = os.path.join(data_folder, "lotr.str")
        
        # Source file based on language selection
        selected_language = self.language.get().lower()
        
        if "english" in selected_language:
            source_folder = os.path.join(translations_folder, "en")
        elif "portuguese" in selected_language:
            source_folder = os.path.join(translations_folder, "pt-br")
        else:
            messagebox.showerror("Error", f"Unsupported language: {selected_language}")
            return
            
        source_file = os.path.join(source_folder, "lotr.str")
        
        # Check if source file exists
        if not os.path.exists(source_file):
            messagebox.showerror("Error", f"Language file not found: {source_file}")
            return
            
        try:
            # Copy language file
            shutil.copy2(source_file, target_file)
            
            # Save language selection to registry
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                winreg.SetValueEx(key, "Language", 0, winreg.REG_SZ, self.language.get())
                
            messagebox.showinfo("Success", f"Language changed to {self.language.get()}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to change language: {e}")

    def delete_specific_folders(self, install_path):
        """Delete specific map folders from the mod installation directory."""
        try:
            # Path to the maps folder
            maps_folder = os.path.join(install_path, "maps")
            
            # List of map folders to delete
            map_folders_to_delete = [
                # Adventure maps
                "map mp adventure arthedain",
                "map mp adventure dorwinion",
                "map mp adventure durins folk",
                "map mp adventure rhun",
                "map mp adventure shadow and flame",
                
                # Fortress maps
                "map mp fortress abrakhan",
                "map mp fortress amon sul",
                "map mp fortress barrow of cargast",
                "map mp fortress caras galadhon",
                "map mp fortress carn dum",
                "map mp fortress dimrill gate",
                "map mp fortress dol amroth",
                "map mp fortress dol guldur",
                "map mp fortress durthang",
                "map mp fortress edennogrod",
                "map mp fortress edoras",
                "map mp fortress esgaroth",
                "map mp fortress fornost",
                "map mp fortress framsburg",
                "map mp fortress gundabad",
                "map mp fortress halls of the elvenking",
                "map mp fortress helms deep",
                "map mp fortress hidar",
                "map mp fortress hornburg",
                "map mp fortress ironfoots halls",
                "map mp fortress isengard",
                "map mp fortress kingdom of erebor",
                "map mp fortress last homely house",
                "map mp fortress minas morgul",
                "map mp fortress minas tirith",
                "map mp fortress pelargir",
                "map mp fortress the angle",
                "map mp fortress the dwarf hold",
                "map mp fortress thorins halls",
                "map mp fortress umbar",
                "map mp fortress wulfborg"
            ]
            
            self.status_label.config(text="Performing post-installation cleanup...", fg="blue")
            self.update()
            
            for map_folder in map_folders_to_delete:
                folder_path = os.path.join(maps_folder, map_folder)
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    self.status_label.config(text=f"Cleaning up: Removing {map_folder}...", fg="blue")
                    self.update()
                    shutil.rmtree(folder_path)
                    print(f"Deleted map folder: {folder_path}")
            
            self.status_label.config(text="Map cleanup completed successfully.", fg="green")
            self.update()
        except Exception as e:
            print(f"Error during map cleanup: {e}")
            self.status_label.config(text=f"Warning: Map cleanup failed - {str(e)}", fg="orange")
            self.update()

    def download_and_extract_mod(self):
        """Downloads and installs the mod."""
        install_path = self.install_folder.get()
        if not install_path:
            self.status_label.config(text="No installation folder selected.", fg="red")
            return

        try:
            # Hide the Download button during the download process
            self.hide_download_button()
            self.hide_play_button()  # Hide play button during installation
            self.progress.pack()  # Show progress bar
            
            # Get remote version for comparison
            remote_version = self.get_remote_version()
            
            # Determine if this is a new installation or an update
            version_file = os.path.join(install_path, "realms_version.json")
            is_update = False
            
            if os.path.exists(version_file):
                try:
                    with open(version_file, "r") as file:
                        content = file.read().strip()
                        if content:
                            local_version = json.loads(content).get("version", "unknown")
                            is_update = True
                except:
                    is_update = False
            
            # Choose the appropriate download URL
            download_url = UPDATE_ZIP_URL if is_update else BASE_MOD_ZIP_URL
            zip_path = os.path.join(install_path, "mod.zip" if not is_update else "update.zip")
            
            # Update status
            if is_update:
                self.status_label.config(text=f"Downloading update to version {remote_version}...", fg="blue")
            else:
                self.status_label.config(text=f"Downloading base mod version {BASE_MOD_VERSION}...", fg="blue")
            
            self.update()

            # Download the ZIP file
            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            with open(zip_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        self.progress["value"] = (downloaded_size / total_size) * 100
                        self.update()

            # Update status during installation
            if is_update:
                self.status_label.config(text="Installing update...", fg="blue")
            else:
                self.status_label.config(text="Installing base mod...", fg="blue")
                
            self.update()

            # Extract the ZIP file
            with ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(install_path)

            os.remove(zip_path)  # Remove the downloaded ZIP file
            
            # Delete specific map folders after installation
            self.delete_specific_folders(install_path)

            # Save the installed version
            with open(version_file, "w") as file:
                json.dump({"version": remote_version}, file)

            # Update status and enable uninstall button
            self.status_label.config(text="Mod installed successfully!", fg="green")
            self.uninstall_button.config(state="normal")  # Enable the Uninstall button
            self.progress.pack_forget()  # Hide progress bar
            self.save_folder(install_path, installed=True)
            
            # Apply the language
            self.change_language()
            
            # Enable language dropdown
            self.language_dropdown.config(state="readonly")
            
            # Show play button
            self.show_play_button()

            # Automatically create a shortcut
            # self.create_shortcut()

            # Update UI after installation
            self.check_for_mod_updates()  # Force an update of the UI

        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.progress.pack_forget()  # Hide progress bar
            self.show_download_button()  # Show the Download button again if there's an error
            self.hide_play_button()  # Hide play button on error

    def get_remote_version(self):
        """Fetches the remote mod version."""
        try:
            response = requests.get(MOD_INFO_URL)
            if response.status_code == 200:
                return response.json().get("version", "0.0.0")
        except Exception as e:
            print(f"Error fetching remote version: {e}")
        return "0.0.0"

    def launch_game(self):
        """Launches the game with the mod."""
        try:
            # Locate the game executable from the registry
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Electronic Arts\Electronic Arts\The Lord of the Rings, The Rise of the Witch-king") as key:
                game_install_path, _ = winreg.QueryValueEx(key, "InstallPath")

            # Get the exact path to the game executable
            game_executable = os.path.normpath(os.path.join(game_install_path, "lotrbfme2ep1.exe"))
            
            # Check if executable exists
            if not os.path.exists(game_executable):
                messagebox.showerror("Error", f"Could not find the game executable at: {game_executable}")
                return

            # Get the mod folder
            mod_folder = os.path.normpath(self.install_folder.get())

            # Create the command line with mod parameter
            cmd = f'"{game_executable}" -mod "{mod_folder}"'
            print(f"Executing command: {cmd}")
            
            # Launch the game
            subprocess.Popen(cmd, shell=True)
            
            # Minimize the launcher window after launching
            self.iconify()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch the game: {e}")

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
                self.hide_play_button()  # Hide the Play button
                self.uninstall_button.config(state="disabled")  # Disable the Uninstall button (no hiding)
                self.create_shortcut_button.config(state="disabled")  # Disable the Shortcut button
                self.folder_button.config(state="normal")  # Enable the Select Folder button
                self.language_dropdown.config(state="disabled")  # Disable language dropdown

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

    def check_launcher_update(self):
        """Check if the launcher is up-to-date and prompt for update if necessary."""
        try:
            # Fetch the version.json file from the MOD_INFO_URL
            print(f"Fetching version.json from: {MOD_INFO_URL}")
            response = requests.get(MOD_INFO_URL)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                version_data = response.json()
                print(f"Response content: {version_data}")  # Log the parsed JSON
                
                # Extract launcher version from JSON
                latest_launcher_version = version_data.get("launcher_version", "0.0.0")
                print(f"Latest launcher version: {latest_launcher_version}")
                print(f"Current launcher version: {LAUNCHER_VERSION}")
                
                # Compare current launcher version with the latest
                if self.is_newer_version(LAUNCHER_VERSION, latest_launcher_version):
                    print("New launcher version detected!")
                    user_choice = messagebox.askyesno(
                        "Launcher Update Available",
                        f"A new launcher version ({latest_launcher_version}) is available. Update now?"
                    )
                    if user_choice:
                        self.update_launcher()
                    else:
                        self.destroy()  # Close the application if the user clicks "No"
                else:
                    print(f"Launcher is up-to-date ({LAUNCHER_VERSION}).")
            else:
                messagebox.showerror("Update Check Failed", "Failed to fetch version.json.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check for launcher updates: {e}")
            self.destroy()  # Ensure the application closes in case of an error

    def is_newer_version(self, current_version, latest_version):
        """Compares two version strings numerically."""
        try:
            current_parts = list(map(int, current_version.split(".")))
            latest_parts = list(map(int, latest_version.split(".")))
            print(f"Comparing versions: {current_parts} < {latest_parts}")
            return latest_parts > current_parts
        except ValueError:
            print("Error parsing version strings for comparison.")
            return False

    def update_launcher(self):
        """Downloads and installs the updated launcher."""
        try:
            # Determine the folder where this executable or script is located
            if getattr(sys, 'frozen', False):
                # Running in a PyInstaller bundle
                exe_dir = os.path.dirname(sys.executable)
            else:
                # Running as a normal Python script
                exe_dir = os.path.dirname(os.path.abspath(__file__))

            zip_filename = "realms_launcher.zip"
            zip_path = os.path.join(exe_dir, zip_filename)

            response = requests.get(LAUNCHER_ZIP_URL, stream=True)
            if response.status_code != 200:
                raise Exception(f"Unexpected status code: {response.status_code}")

            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            with open(zip_path, "wb") as file:
                # Increase chunk_size to 8192 for more efficient downloads
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size:
                            self.progress["value"] = (downloaded_size / total_size) * 100
                        self.update()

            messagebox.showinfo(
                "Launcher Update",
                f"The updated launcher has been downloaded to:\n\n{zip_path}\n\nPlease extract it manually."
            )

            # Open the folder where the file was saved
            os.startfile(exe_dir)

            # Exit the current launcher
            self.quit()

        except Exception as e:
            messagebox.showerror("Update Failed", f"Failed to update the launcher: {e}")

if __name__ == "__main__":
    app = ModLauncher()
    app.mainloop()