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
import subprocess  # Import subprocess for launching the game
import rarfile  # Import rarfile for RAR extraction
import ctypes  # Import ctypes for admin privileges check
import psutil  # Import psutil for process management

# Constants
MOD_INFO_URL = "https://realmsinexile.s3.us-east-005.backblazeb2.com/version.json"
BASE_MOD_VERSION = "0.8.0"  # Base version of the mod
BASE_MOD_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms.zip"  # Base mod download
UPDATE_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_update.zip"  # Update package
AOTR_RAR_URL = "https://f005.backblazeb2.com/file/RealmsInExile/aotr.rar"  # AOTR download
LAUNCHER_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_launcher.zip"  # Launcher update package
NEWS_URL = "https://raw.githubusercontent.com/hansnery/Realms-Launcher/refs/heads/main/news.html"
LAUNCHER_VERSION = "1.0.4"  # Updated launcher version
REG_PATH = r"SOFTWARE\REALMS_Launcher"


def is_admin():
    """Check if the application is running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """Restart the application with admin privileges."""
    try:
        if getattr(sys, 'frozen', False):
            # Running in a PyInstaller bundle
            script = sys.executable
        else:
            # Running as a normal Python script
            script = sys.argv[0]
        
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, script, None, 1
        )
        return True
    except Exception as e:
        print(f"Error running as admin: {e}")
        return False


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
        
        # Check for admin privileges on startup only if running as compiled exe
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen and not is_admin():
            self.check_admin_privileges()
        
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

    def check_admin_privileges(self):
        """Check if running with admin privileges and prompt user if not."""
        if not is_admin():
            result = messagebox.askyesno(
                "Admin Privileges Required",
                "This launcher requires administrator privileges to function "
                "properly.\n\n"
                "Would you like to restart the application with admin "
                "privileges?\n\n"
                "Note: This will close the current instance and restart with "
                "elevated permissions.",
                icon="warning"
            )
            
            if result:
                # Try to restart with admin privileges
                if run_as_admin():
                    # Close the current instance
                    self.quit()
                    sys.exit(0)
                else:
                    messagebox.showerror(
                        "Error",
                        "Failed to restart with admin privileges.\n"
                        "Please run the launcher as administrator manually."
                    )
                    # Continue without admin privileges 
                    # (user chose to proceed anyway)
            else:
                # User chose not to restart, show warning but continue
                messagebox.showwarning(
                    "Limited Functionality",
                    "The launcher will continue without admin privileges.\n"
                    "Some features may not work correctly.\n\n"
                    "To ensure full functionality, please run the launcher as "
                    "administrator."
                )

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
        Tooltip(self.folder_button, "Select AgeoftheRing folder.")

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
            # Check if the selected folder contains an "aotr" subfolder
            aotr_folder = os.path.join(folder, "aotr")
            if not os.path.exists(aotr_folder) or not os.path.isdir(aotr_folder):
                messagebox.showwarning(
                    "Invalid Folder",
                    "The selected folder does not contain an 'aotr' subfolder.\n\n"
                    "Please select the correct Age of the Ring folder that contains "
                    "the 'aotr' subfolder."
                )
                self.status_label.config(
                    text="Please select the correct Age of the Ring folder.", 
                    fg="red"
                )
                self.hide_download_button()
                self.hide_play_button()
                return
            
            self.install_folder.set(folder)
            self.folder_label.config(text=f"Installation Folder: {folder}")
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
        realms_folder = os.path.join(install_path, "realms")
        version_file = os.path.join(realms_folder, "realms_version.json")

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
                    # Get the Realms in Exile version for display
                    try:
                        response = requests.get(MOD_INFO_URL)
                        if response.status_code == 200:
                            realms_version = response.json().get("version", BASE_MOD_VERSION)
                        else:
                            realms_version = BASE_MOD_VERSION
                    except:
                        realms_version = BASE_MOD_VERSION
                    self.status_label.config(text=f"Realms in Exile not found. Ready to download version {realms_version}.", fg="green")
                    self.download_button.config(text="Download Files", state="normal")
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
            
        # Data folder path (now in realms folder)
        realms_folder = os.path.join(install_path, "realms")
        data_folder = os.path.join(realms_folder, "data")
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
            # Path to the maps folder (now in realms folder)
            realms_folder = os.path.join(install_path, "realms")
            maps_folder = os.path.join(realms_folder, "maps")
            
            # List of map folders to delete
            map_folders_to_delete = [
                # Adventure maps
                "map mp alternate arthedain",
                "map mp alternate dorwinion",
                "map mp alternate durins folk",
                "map mp alternate rhun",
                "map mp alternate shadow and flame",
                
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

    def verify_folder_copy(self, source_folder, dest_folder):
        """Verifies that the destination folder is a complete copy of the source folder."""
        try:
            # Check if both folders exist
            if not os.path.exists(source_folder):
                return False, "Source folder does not exist"
            if not os.path.exists(dest_folder):
                return False, "Destination folder does not exist"
            
            # Get file lists from both folders
            source_files = []
            dest_files = []
            
            for root, dirs, files in os.walk(source_folder):
                rel_path = os.path.relpath(root, source_folder)
                for file in files:
                    source_files.append(os.path.join(rel_path, file))
            
            for root, dirs, files in os.walk(dest_folder):
                rel_path = os.path.relpath(root, dest_folder)
                for file in files:
                    dest_files.append(os.path.join(rel_path, file))
            
            # Check if file lists match
            if set(source_files) != set(dest_files):
                missing_files = set(source_files) - set(dest_files)
                extra_files = set(dest_files) - set(source_files)
                return False, f"File mismatch. Missing: {len(missing_files)}, Extra: {len(extra_files)}"
            
            # Check file sizes and modification times for a sample of files
            sample_files = source_files[:min(50, len(source_files))]  # Check first 50 files
            for file_path in sample_files:
                source_file = os.path.join(source_folder, file_path)
                dest_file = os.path.join(dest_folder, file_path)
                
                if not os.path.exists(dest_file):
                    return False, f"Destination file missing: {file_path}"
                
                # Compare file sizes
                if os.path.getsize(source_file) != os.path.getsize(dest_file):
                    return False, f"File size mismatch: {file_path}"
            
            return True, "Copy verification successful"
            
        except Exception as e:
            return False, f"Verification error: {str(e)}"

    def prepare_realms_folder(self, install_path):
        """Creates a copy of the 'aotr' folder and renames it to 'realms'."""
        aotr_folder = os.path.join(install_path, "aotr")
        realms_folder = os.path.join(install_path, "realms")
        
        # Check if aotr folder exists
        if not os.path.exists(aotr_folder):
            raise Exception("'aotr' folder not found in the installation directory")
        
        # Check if realms folder already exists and verify it
        if os.path.exists(realms_folder):
            self.status_label.config(text="Verifying existing realms folder...", fg="blue")
            self.update()
            
            is_valid, message = self.verify_folder_copy(aotr_folder, realms_folder)
            
            if is_valid:
                self.status_label.config(text="Existing realms folder is valid.", fg="green")
                self.update()
                return realms_folder
            else:
                self.status_label.config(text=f"Invalid realms folder detected: {message}. Removing...", fg="orange")
                self.update()
                shutil.rmtree(realms_folder)
        
        # Copy aotr folder to realms
        self.status_label.config(text="Copying AOTR folder...", fg="blue")
        self.update()
        
        try:
            shutil.copytree(aotr_folder, realms_folder)
        except Exception as e:
            # If copy fails, clean up partial copy
            if os.path.exists(realms_folder):
                shutil.rmtree(realms_folder)
            raise Exception(f"Failed to copy AOTR folder: {str(e)}")
        
        # Verify the copy was successful
        self.status_label.config(text="Verifying copy integrity...", fg="blue")
        self.update()
        
        is_valid, message = self.verify_folder_copy(aotr_folder, realms_folder)
        
        if not is_valid:
            # Clean up failed copy
            if os.path.exists(realms_folder):
                shutil.rmtree(realms_folder)
            raise Exception(f"Copy verification failed: {message}")
        
        self.status_label.config(text="Realms folder prepared successfully.", fg="green")
        self.update()
        
        return realms_folder

    def download_and_extract_mod(self):
        """Downloads and installs the mod."""
        install_path = self.install_folder.get()
        if not install_path:
            self.status_label.config(text="No installation folder selected.", fg="red")
            return

        try:
            # Disable folder selection during download/installation
            self.folder_button.config(state="disabled")
            
            # Hide the Download button during the download process
            self.hide_download_button()
            self.hide_play_button()  # Hide play button during installation
            self.progress.pack()  # Show progress bar
            
            # Check for existing AOTR RAR file from previous failed installation
            existing_rar_path = os.path.join(install_path, "aotr.rar")
            
            # Check AOTR version and download if needed
            aotr_updated, aotr_rar_path = self.check_aotr_version(install_path)
            
            # If we found an existing RAR file, we need to extract it
            if aotr_updated and aotr_rar_path and os.path.exists(aotr_rar_path):
                # Check if realms folder already exists
                realms_folder = os.path.join(install_path, "realms")
                if not os.path.exists(realms_folder) or not os.path.isdir(realms_folder):
                    self.status_label.config(text="Extracting existing AOTR RAR file...", fg="blue")
                    self.update()
                    try:
                        # Try to extract the RAR file
                        with rarfile.RarFile(aotr_rar_path, "r") as rar_ref:
                            rar_ref.extractall(install_path)
                            
                            # If the RAR contains an 'aotr' folder, rename it to 'realms'
                            extracted_aotr = os.path.join(install_path, "aotr")
                            if os.path.exists(extracted_aotr):
                                os.rename(extracted_aotr, realms_folder)
                            else:
                                # If no 'aotr' folder in RAR, create realms folder and move contents
                                os.makedirs(realms_folder, exist_ok=True)
                                # Move all files from install_path to realms_folder (except the RAR file)
                                for item in os.listdir(install_path):
                                    item_path = os.path.join(install_path, item)
                                    if os.path.isfile(item_path) and item != "aotr.rar":
                                        shutil.move(item_path, os.path.join(realms_folder, item))
                                    elif os.path.isdir(item_path) and item != "realms":
                                        shutil.move(item_path, os.path.join(realms_folder, item))
                        
                        self.status_label.config(text="Successfully extracted existing AOTR RAR file", fg="green")
                        self.update()
                        
                    except Exception as extract_error:
                        print(f"Failed to extract existing RAR file: {extract_error}")
                        self.status_label.config(text="Failed to extract existing RAR file, continuing...", fg="orange")
                        self.update()
                        # Reset aotr_updated since extraction failed
                        aotr_updated = False
                        aotr_rar_path = None
            
            # If no RAR path was returned but we have an existing RAR file, use it
            if not aotr_rar_path and os.path.exists(existing_rar_path):
                aotr_rar_path = existing_rar_path
                print(f"Found existing AOTR RAR file: {existing_rar_path}")
            
            # Check if we need to extract the RAR file (if it exists but realms folder is missing/incomplete)
            realms_folder = os.path.join(install_path, "realms")
            if aotr_rar_path and os.path.exists(aotr_rar_path) and (not os.path.exists(realms_folder) or not os.path.isdir(realms_folder)):
                self.status_label.config(text="Attempting to extract existing AOTR RAR file...", fg="blue")
                self.update()
                try:
                    # Try to extract the RAR file
                    with rarfile.RarFile(aotr_rar_path, "r") as rar_ref:
                        rar_ref.extractall(install_path)
                        
                        # If the RAR contains an 'aotr' folder, rename it to 'realms'
                        extracted_aotr = os.path.join(install_path, "aotr")
                        if os.path.exists(extracted_aotr):
                            os.rename(extracted_aotr, realms_folder)
                        else:
                            # If no 'aotr' folder in RAR, create realms folder and move contents
                            os.makedirs(realms_folder, exist_ok=True)
                            # Move all files from install_path to realms_folder (except the RAR file)
                            for item in os.listdir(install_path):
                                item_path = os.path.join(install_path, item)
                                if os.path.isfile(item_path) and item != "aotr.rar":
                                    shutil.move(item_path, os.path.join(realms_folder, item))
                                elif os.path.isdir(item_path) and item != "realms":
                                    shutil.move(item_path, os.path.join(realms_folder, item))
                    
                    self.status_label.config(text="Successfully extracted existing AOTR RAR file", fg="green")
                    self.update()
                    aotr_updated = True  # Mark as updated since we extracted the RAR
                    
                except Exception as extract_error:
                    print(f"Failed to extract existing RAR file: {extract_error}")
                    self.status_label.config(text="Failed to extract existing RAR file, continuing...", fg="orange")
                    self.update()
            
            # Get remote version for comparison
            remote_version = self.get_remote_version()
            
            # Prepare the realms folder based on whether AOTR was updated
            if aotr_updated:
                # AOTR was downloaded and extracted directly to realms folder
                self.status_label.config(text="AOTR extracted to realms folder...", fg="blue")
                self.update()
            else:
                # Use existing aotr folder, copy it to realms
                realms_folder = self.prepare_realms_folder(install_path)
            
            # Ensure realms folder exists before proceeding
            if not os.path.exists(realms_folder) or not os.path.isdir(realms_folder):
                raise Exception("Realms folder not found. AOTR extraction failed and no fallback available.")
            
            # Determine if this is a new installation or an update
            version_file = os.path.join(realms_folder, "realms_version.json")
            is_update = False
            needs_base_first = False
            local_version = "not installed"
            
            if os.path.exists(version_file):
                try:
                    with open(version_file, "r") as file:
                        content = file.read().strip()
                        if content:
                            local_version = json.loads(content).get("version", "unknown")
                            is_update = True
                            
                            # Check if local version is lower than base version
                            if self.is_lower_version(local_version, BASE_MOD_VERSION):
                                needs_base_first = True
                except:
                    is_update = False
            
            # First install base version if needed
            if needs_base_first:
                self.status_label.config(text=f"Installing base version {BASE_MOD_VERSION}...", fg="blue")
                self.update()
                
                # Download and install base version
                self.download_and_install_package(realms_folder, BASE_MOD_ZIP_URL, "base mod", BASE_MOD_VERSION)
                
                # Update local version to base version
                with open(version_file, "w") as file:
                    json.dump({"version": BASE_MOD_VERSION}, file)
                
                # Now we need to check if we need to update further
                if self.is_lower_version(BASE_MOD_VERSION, remote_version):
                    self.status_label.config(text=f"Base version installed. Now updating to version {remote_version}...", fg="blue")
                    self.update()
                    self.download_and_install_package(realms_folder, UPDATE_ZIP_URL, "update", remote_version)
                    
                    # Update to remote version
                    with open(version_file, "w") as file:
                        json.dump({"version": remote_version}, file)
            else:
                # Always download Realms after AOTR (AOTR might not contain the latest Realms)
                if aotr_updated:
                    # Choose the appropriate download URL
                    download_url = UPDATE_ZIP_URL if is_update else BASE_MOD_ZIP_URL
                    version_label = "update" if is_update else "base mod"
                    version_number = remote_version if is_update else BASE_MOD_VERSION
                    
                    self.download_and_install_package(realms_folder, download_url, version_label, version_number)
                    
                    # Save the installed version
                    with open(version_file, "w") as file:
                        json.dump({"version": remote_version if is_update else BASE_MOD_VERSION}, file)
                else:
                    # Only download Realms if AOTR wasn't updated (since AOTR already contains Realms)
                    # Choose the appropriate download URL
                    download_url = UPDATE_ZIP_URL if is_update else BASE_MOD_ZIP_URL
                    version_label = "update" if is_update else "base mod"
                    version_number = remote_version if is_update else BASE_MOD_VERSION
                    
                    self.download_and_install_package(realms_folder, download_url, version_label, version_number)
                    
                    # Save the installed version
                    with open(version_file, "w") as file:
                        json.dump({"version": remote_version if is_update else BASE_MOD_VERSION}, file)

            # Delete the AOTR RAR file after realms.zip is successfully extracted
            if aotr_rar_path and os.path.exists(aotr_rar_path):
                try:
                    # Only delete if Realms installation was successful
                    if os.path.exists(realms_folder) and os.path.isdir(realms_folder):
                        os.remove(aotr_rar_path)
                        print(f"Deleted AOTR RAR file: {aotr_rar_path}")
                    else:
                        print(f"Keeping AOTR RAR file for recovery: {aotr_rar_path}")
                except Exception as e:
                    print(f"Warning: Could not delete AOTR RAR file: {e}")
            elif aotr_updated:
                print("AOTR RAR file was already deleted during fallback process")

            # Update status and enable uninstall button
            self.status_label.config(text="Mod installed successfully!", fg="green")
            self.uninstall_button.config(state="normal")  # Enable the Uninstall button
            self.progress.pack_forget()  # Hide progress bar
            self.save_folder(install_path, installed=True)
            
            # Re-enable folder selection
            self.folder_button.config(state="normal")
            
            # Apply the language
            self.change_language()
            
            # Enable language dropdown
            self.language_dropdown.config(state="readonly")
            
            # Show play button
            self.show_play_button()

            # Update UI after installation
            self.check_for_mod_updates()  # Force an update of the UI

        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.progress.pack_forget()  # Hide progress bar
            self.show_download_button()  # Show the Download button again if there's an error
            self.hide_play_button()  # Hide play button on error
            
            # Re-enable folder selection on error
            self.folder_button.config(state="normal")

    def download_and_install_package(self, install_path, download_url, version_label, version_number):
        """Helper method to download and install a specific package."""
        # Update status
        if version_label == "base mod":
            self.status_label.config(text=f"Downloading Realms in Exile version {version_number}...", fg="blue")
        else:
            self.status_label.config(text=f"Downloading {version_label} version {version_number}...", fg="blue")
        self.update()
        
        # Create a temporary file name in the parent directory to avoid nesting
        parent_dir = os.path.dirname(install_path)
        zip_path = os.path.join(parent_dir, f"{version_label.replace(' ', '_')}.zip")
        
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
        self.status_label.config(text=f"Installing {version_label}...", fg="blue")
        self.update()

        # Extract the ZIP file to the parent directory (AgeoftheRing root)
        parent_dir = os.path.dirname(install_path)
        with ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(parent_dir)

        # Remove the downloaded ZIP file
        os.remove(zip_path)
        
        # Delete specific map folders after installation
        self.delete_specific_folders(install_path)
        
        self.status_label.config(text=f"{version_label.capitalize()} version {version_number} installed successfully", fg="green")
        self.update()

    def is_lower_version(self, version1, version2):
        """Compares two version strings and returns True if version1 is lower than version2."""
        try:
            v1_parts = list(map(int, version1.split(".")))
            v2_parts = list(map(int, version2.split(".")))
            
            # Pad with zeros if needed
            while len(v1_parts) < len(v2_parts):
                v1_parts.append(0)
            while len(v2_parts) < len(v1_parts):
                v2_parts.append(0)
                
            # Compare version parts
            for i in range(len(v1_parts)):
                if v1_parts[i] < v2_parts[i]:
                    return True
                elif v1_parts[i] > v2_parts[i]:
                    return False
                    
            # If we get here, versions are equal
            return False
        except ValueError:
            # If we can't parse the versions, assume we need an update
            return True

    def get_remote_version(self):
        """Fetches the remote mod version."""
        try:
            response = requests.get(MOD_INFO_URL)
            if response.status_code == 200:
                return response.json().get("version", "0.0.0")
        except Exception as e:
            print(f"Error fetching remote version: {e}")
        return "0.0.0"

    def get_aotr_version_from_str_file(self, install_path):
        """Parses AOTR version from the lotr.str file."""
        try:
            aotr_data_path = os.path.join(install_path, "aotr", "data", "lotr.str")
            if not os.path.exists(aotr_data_path):
                print(f"AOTR data file not found: {aotr_data_path}")
                return "0.0.0"
            
            with open(aotr_data_path, 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
                
                # Look for the active (uncommented) version line
                import re
                version_pattern = r'"Age of the Ring Version (\d+\.\d+(?:\.\d+)?)"'
                
                for line in lines:
                    line = line.strip()
                    # Skip commented lines (lines starting with //)
                    if line.startswith('//'):
                        continue
                    
                    # Look for the version pattern in non-commented lines
                    match = re.search(version_pattern, line)
                    if match:
                        version = match.group(1)
                        print(f"Found AOTR version in lotr.str: {version}")
                        return version
                
                print("Could not find active AOTR version in lotr.str file")
                return "0.0.0"
                    
        except Exception as e:
            print(f"Error parsing AOTR version from lotr.str: {e}")
            return "0.0.0"

    def get_aotr_version_info(self):
        """Fetches AOTR version information from the remote version file."""
        try:
            response = requests.get(MOD_INFO_URL)
            if response.status_code == 200:
                data = response.json()
                return {
                    "required_aotr_version": data.get("required_aotr_version", "0.0.0"),
                    "current_aotr_version": data.get("current_aotr_version", "0.0.0")
                }
        except Exception as e:
            print(f"Error fetching AOTR version info: {e}")
        return {"required_aotr_version": "0.0.0", "current_aotr_version": "0.0.0"}

    def check_aotr_version(self, install_path):
        """Checks if the AOTR version is compatible and downloads if needed."""
        try:
            # Get AOTR version info from remote
            aotr_info = self.get_aotr_version_info()
            required_version = aotr_info["required_aotr_version"]
            
            # Get current AOTR version from local lotr.str file
            current_version = self.get_aotr_version_from_str_file(install_path)
            
            # Check if current AOTR version is greater than or equal to required
            if self.is_lower_version(current_version, required_version):
                # Check if aotr.rar already exists locally
                existing_rar_path = os.path.join(install_path, "aotr.rar")
                if os.path.exists(existing_rar_path):
                    print(f"Found existing AOTR RAR file: {existing_rar_path}")
                    self.status_label.config(
                        text="Found existing AOTR RAR file. Extracting...", fg="blue"
                    )
                    self.update()
                    return True, existing_rar_path
                else:
                    self.status_label.config(
                        text=f"Realms in Exile requires AOTR {required_version}. "
                             f"Current version: {current_version}. Downloading...", fg="blue"
                    )
                    self.update()
                    
                    # Download and install AOTR
                    rar_path = self.download_and_install_aotr(install_path, required_version)
                    return True, rar_path
            else:
                print(f"AOTR version {current_version} is compatible (required: {required_version})")
                return False, None
                
        except Exception as e:
            print(f"Error checking AOTR version: {e}")
            return False, None

    def download_and_install_aotr(self, install_path, aotr_version):
        """Downloads and installs the AOTR mod."""
        try:
            # Update status - keep the informative message from check_aotr_version
            # Don't overwrite the status message here since it's already set in check_aotr_version
            self.update()
            
            # Create a temporary file name
            rar_path = os.path.join(install_path, "aotr.rar")
            
            # Download the RAR file
            response = requests.get(AOTR_RAR_URL, stream=True)
            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            with open(rar_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            self.progress["value"] = (downloaded_size / total_size) * 100
                        self.update()

            # Update status during installation
            self.status_label.config(text="Installing AOTR...", fg="blue")
            self.update()

            # Remove existing realms folder if it exists
            realms_folder = os.path.join(install_path, "realms")
            if os.path.exists(realms_folder):
                self.status_label.config(text="Removing existing realms folder...", fg="blue")
                self.update()
                shutil.rmtree(realms_folder)

            # Try to extract the RAR file
            try:
                with rarfile.RarFile(rar_path, "r") as rar_ref:
                    rar_ref.extractall(install_path)
                    
                    # If the RAR contains an 'aotr' folder, rename it to 'realms'
                    extracted_aotr = os.path.join(install_path, "aotr")
                    if os.path.exists(extracted_aotr):
                        os.rename(extracted_aotr, realms_folder)
                    else:
                        # If no 'aotr' folder in RAR, create realms folder and move contents
                        os.makedirs(realms_folder, exist_ok=True)
                        # Move all files from install_path to realms_folder (except the RAR file)
                        for item in os.listdir(install_path):
                            item_path = os.path.join(install_path, item)
                            if os.path.isfile(item_path) and item != "aotr.rar":
                                shutil.move(item_path, os.path.join(realms_folder, item))
                            elif os.path.isdir(item_path) and item != "realms":
                                shutil.move(item_path, os.path.join(realms_folder, item))
                
                self.status_label.config(text=f"AOTR version {aotr_version} extracted successfully", fg="green")
                self.update()
                
            except Exception as rar_error:
                print(f"RAR extraction failed: {rar_error}")
                self.status_label.config(text="RAR extraction failed, checking AOTR version...", fg="orange")
                self.update()
                
                # Show a helpful message about installing RAR tools
                if "Cannot find working tool" in str(rar_error):
                    print("Note: To extract RAR files, install a RAR extraction tool like:")
                    print("  - WinRAR: https://www.win-rar.com/")
                    print("  - 7-Zip: https://7-zip.org/")
                    print("  - Or use the command line: choco install unrar")
                
                # Check if we should use existing AOTR folder based on version requirements
                aotr_info = self.get_aotr_version_info()
                required_version = aotr_info["required_aotr_version"]
                current_version = self.get_aotr_version_from_str_file(install_path)
                
                # Only use existing AOTR if current version is compatible (not lower than required)
                if self.is_lower_version(current_version, required_version):
                    # Current AOTR version is lower than required, don't use it
                    raise Exception(f"RAR extraction failed. Current AOTR version ({current_version}) is lower than required ({required_version}). Please install a RAR extraction tool to proceed.")
                else:
                    # Current AOTR version is compatible, use existing folder as fallback
                    existing_aotr = os.path.join(install_path, "aotr")
                    if os.path.exists(existing_aotr):
                        shutil.copytree(existing_aotr, realms_folder)
                        self.status_label.config(text="Using existing AOTR folder as fallback", fg="green")
                        self.update()
                    else:
                        raise Exception("RAR extraction failed and no existing AOTR folder found")
                    
                    # Delete the downloaded RAR file since we couldn't use it
                    if os.path.exists(rar_path):
                        os.remove(rar_path)
                    return None  # No RAR file to track since we deleted it
            
            # Don't delete the RAR file here - return the path instead
            # os.remove(rar_path)  # Commented out - will be deleted later
            
            self.status_label.config(text=f"AOTR version {aotr_version} installed successfully", fg="green")
            self.update()
            
            # Return the RAR file path so it can be deleted after realms.zip extraction
            return rar_path
            
        except Exception as e:
            print(f"Error downloading AOTR: {e}")
            self.status_label.config(text=f"Error downloading AOTR: {e}", fg="red")
            self.update()
            raise e

    def launch_game(self):
        """Launches the game with the mod."""
        try:
            # Get the installation folder and look for the game executable in the rotwk subfolder
            install_path = os.path.normpath(self.install_folder.get())
            rotwk_folder = os.path.join(install_path, "rotwk")
            game_executable = os.path.normpath(os.path.join(rotwk_folder, "lotrbfme2ep1.exe"))
            
            # Check if executable exists
            if not os.path.exists(game_executable):
                messagebox.showerror("Error", f"Could not find the game executable at: {game_executable}")
                return

            # Get the mod folder (now the realms folder)
            mod_folder = os.path.join(install_path, "realms")

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
            "Do you really want to uninstall the Realms in Exile mod? This will not delete your Age of the Ring mod."
        ):
            try:
                # Only delete the realms folder, not the entire installation directory
                realms_folder = os.path.join(folder, "realms")
                if os.path.exists(realms_folder):
                    shutil.rmtree(realms_folder)
                    print(f"Deleted realms folder: {realms_folder}")
                else:
                    print("Realms folder not found, nothing to delete")

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
            # Get the installation folder and look for the game executable in the rotwk subfolder
            install_path = os.path.normpath(self.install_folder.get())
            rotwk_folder = os.path.join(install_path, "rotwk")
            game_executable = os.path.normpath(os.path.join(rotwk_folder, "lotrbfme2ep1.exe"))
            
            if not os.path.exists(game_executable):
                messagebox.showerror("Error", f"Could not find the game executable at: {game_executable}")
                return

            # Get the mod folder and verify the icon file
            mod_folder = os.path.join(install_path, "realms")
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
                current_exe = sys.executable
            else:
                # Running as a normal Python script
                exe_dir = os.path.dirname(os.path.abspath(__file__))
                current_exe = os.path.abspath(__file__)

            zip_filename = "realms_launcher.zip"
            zip_path = os.path.join(exe_dir, zip_filename)
            update_script_path = os.path.join(exe_dir, "update_launcher.py")

            # Download the launcher update
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

            # Create the update script
            self.create_update_script(update_script_path, exe_dir, zip_path, current_exe)

            # Show success message
            messagebox.showinfo(
                "Launcher Update",
                "The launcher update has been downloaded.\n\n"
                "The launcher will now close and automatically update itself.\n"
                "Please wait for the update to complete."
            )

            # Start the update script and exit
            subprocess.Popen([sys.executable, update_script_path], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            # Exit the current launcher
            self.quit()

        except Exception as e:
            messagebox.showerror("Update Failed", f"Failed to update the launcher: {e}")

    def create_update_script(self, script_path, exe_dir, zip_path, current_exe):
        """Creates a Python script that will handle the launcher update."""
        script_content = f'''import os
import sys
import time
import zipfile
import shutil
import subprocess
import threading

def wait_for_process_to_exit(process_name, timeout=30):
    """Wait for a process to exit."""
    import psutil
    start_time = time.time()
    while time.time() - start_time < timeout:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    return False  # Process still running
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(0.5)
    return True  # Process exited or timeout

def update_launcher():
    """Update the launcher by extracting the zip and replacing the executable."""
    try:
        # Wait a moment for the main launcher to close
        time.sleep(2)
        
        # Check if the main launcher process has exited
        if getattr(sys, 'frozen', False):
            process_name = "realms_launcher.exe"
        else:
            process_name = "python.exe"
        
        # Wait for the main launcher to exit
        if not wait_for_process_to_exit(process_name):
            print("Main launcher process still running, waiting...")
            time.sleep(5)
        
        # Extract the zip file
        print("Extracting launcher update...")
        with zipfile.ZipFile("{zip_path}", 'r') as zip_ref:
            zip_ref.extractall("{exe_dir}")
        
        # Find the new executable
        new_exe = None
        for root, dirs, files in os.walk("{exe_dir}"):
            for file in files:
                if file.endswith('.exe') and 'realms_launcher' in file.lower():
                    new_exe = os.path.join(root, file)
                    break
            if new_exe:
                break
        
        if new_exe and new_exe != "{current_exe}":
            # Replace the old executable with the new one
            print(f"Replacing launcher: {{new_exe}}")
            
            # If running as frozen executable, replace it
            if getattr(sys, 'frozen', False):
                # Create a backup of the old executable
                backup_path = "{current_exe}.backup"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                shutil.copy2("{current_exe}", backup_path)
                
                # Replace the executable
                os.remove("{current_exe}")
                shutil.move(new_exe, "{current_exe}")
                
                # Clean up the backup after successful replacement
                if os.path.exists("{current_exe}"):
                    os.remove(backup_path)
            
            # Clean up the zip file
            if os.path.exists("{zip_path}"):
                os.remove("{zip_path}")
            
            print("Launcher update completed successfully!")
            
            # Start the new launcher
            print("Starting updated launcher...")
            subprocess.Popen(["{current_exe}"], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
            
        else:
            print("Could not find new launcher executable")
            
    except Exception as e:
        print(f"Error during launcher update: {{e}}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    update_launcher()
'''
        
        with open(script_path, 'w') as f:
            f.write(script_content)

if __name__ == "__main__":
    app = ModLauncher()
    app.mainloop()