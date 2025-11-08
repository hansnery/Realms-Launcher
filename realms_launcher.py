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
import shutil  # removing directories / copying files
import subprocess  # launching the game
import rarfile  # RAR extraction
import ctypes  # admin privileges check
import tempfile
import pathlib

# =========================
# Config flags
# =========================
# If True, the updater will run elevated (UAC prompt) to write into protected locations.
USE_ELEVATED_UPDATER = False

# =========================
# Constants
# =========================
MOD_INFO_URL = "https://realmsinexile.s3.us-east-005.backblazeb2.com/version_beta.json"
BASE_MOD_VERSION = "0.8.0"  # Base version of the mod
BASE_MOD_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms.zip"  # Base mod download
UPDATE_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_update.zip"  # Update package
AOTR_RAR_URL = "https://f005.backblazeb2.com/file/RealmsInExile/aotr.rar"  # AOTR download
LAUNCHER_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_launcher_beta.zip"  # Launcher update package
NEWS_URL = "https://raw.githubusercontent.com/hansnery/Realms-Launcher/refs/heads/main/news.html"
LAUNCHER_VERSION = "1.0.7"  # Updated launcher version
REG_PATH = r"SOFTWARE\REALMS_Launcher"


# =========================
# Admin helpers
# =========================
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


# =========================
# Self-update helpers (module-level)
# =========================
def _is_frozen():
    return getattr(sys, 'frozen', False)


def _launcher_dir() -> str:
    # Where the launcher lives (EXE dir for frozen, script dir for dev)
    return os.path.dirname(sys.executable) if _is_frozen() else os.path.dirname(os.path.abspath(__file__))


def _launcher_path() -> str:
    # Path to the running launcher (EXE or script)
    return sys.executable if _is_frozen() else os.path.abspath(sys.argv[0])


def _python_cmd() -> list:
    # How to run a .py updater if not frozen
    return [sys.executable]


def _start_detached(cmd: list):
    # Start a detached process on Windows
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(
        cmd,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=True
    )


def _write_updater_ps1(ps1_path: str):
    """
    PowerShell updater with detailed logging:
      - Waits for main process (PID) to exit
      - Mirrors staged -> target via robocopy with retries
      - Logs every step to LogPath
      - Cleans up staged dir
      - Relaunches the launcher with proper working directory
    """
    ps1 = r'''
param(
    [string]$TargetDir,
    [string]$StagedDir,
    [int]$MainPid,
    [string]$RelaunchPath,
    [string]$RelaunchArgs,
    [string]$RelaunchCwd,
    [string]$LogPath
)

# Ensure parent folder exists (esp. if redirected elsewhere)
try {
    $parent = Split-Path -Parent $LogPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
} catch {}

# --- Logging helper ---
function Write-Log {
    param([string]$msg)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss.fff")
    try {
        Add-Content -LiteralPath $LogPath -Value "[$timestamp] $msg"
    } catch {}
}

# Ensure log file exists
try {
    New-Item -ItemType File -Force -Path $LogPath | Out-Null
} catch {}

Write-Log "==== Updater started ===="
Write-Log "TargetDir=$TargetDir"
Write-Log "StagedDir=$StagedDir"
Write-Log "MainPid=$MainPid"
Write-Log "RelaunchPath=$RelaunchPath"
Write-Log "RelaunchArgs=$RelaunchArgs"
Write-Log "RelaunchCwd=$RelaunchCwd"
Write-Log "PSVersion=$($PSVersionTable.PSVersion)"

# Wait for main process to exit (best effort)
if ($MainPid -gt 0) {
    try {
        Write-Log "Waiting for PID $MainPid to exit..."
        Wait-Process -Id $MainPid -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Log "Wait-Process threw: $($_.Exception.Message)"
    }
}

# Copy loop (robust against transient locks)
function Copy-With-Retry {
    param([string]$src, [string]$dst)
    $max = 10
    for ($i=1; $i -le $max; $i++) {
        try {
            if (Test-Path -LiteralPath $src) {
                if (-not (Test-Path -LiteralPath $dst)) {
                    try { New-Item -ItemType Directory -Force -Path $dst | Out-Null } catch {}
                }
                Write-Log "robocopy try #$i"
                # /MIR mirror tree, /R:2 /W:0 quick retries, /NFL/NDL quiets file/dir lists
                robocopy "$src" "$dst" /MIR /R:2 /W:0 /NFL /NDL /NJH /NJS /NP
                $code = $LASTEXITCODE
                Write-Log "robocopy exit code = $code"
                # Robocopy success or benign codes: 0,1,2,3,4,5,6,7
                if ($code -le 7) { return $true }
            } else {
                Write-Log "Staged path not found"
                return $false
            }
        } catch {
            Write-Log "Copy exception: $($_.Exception.Message)"
        }
        Start-Sleep -Milliseconds (200 * $i)
    }
    return $false
}

$ok = Copy-With-Retry -src $StagedDir -dst $TargetDir
Write-Log "Copy result = $ok"

# Cleanup staged folder (best effort)
try {
    if (Test-Path -LiteralPath $StagedDir) {
        Write-Log "Removing staged dir..."
        Remove-Item -LiteralPath $StagedDir -Recurse -Force -ErrorAction SilentlyContinue
    }
} catch {
    Write-Log "Cleanup exception: $($_.Exception.Message)"
}

# Relaunch if requested
if ($ok -and $RelaunchPath) {
    try {
        Write-Log "Relaunching..."
        if (Test-Path -LiteralPath $RelaunchPath) {
            if ($RelaunchArgs) {
                Start-Process -FilePath $RelaunchPath -ArgumentList $RelaunchArgs -WorkingDirectory $RelaunchCwd | Out-Null
            } else {
                Start-Process -FilePath $RelaunchPath -WorkingDirectory $RelaunchCwd | Out-Null
            }
        } else {
            # If path isn't a file, attempt to run it as a command line
            Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile","-WindowStyle","Hidden","-Command",$RelaunchPath -WorkingDirectory $RelaunchCwd | Out-Null
        }
    } catch {
        Write-Log "Relaunch exception: $($_.Exception.Message)"
    }
}

Write-Log "==== Updater finished ===="
exit 0
'''
    with open(ps1_path, 'w', encoding='utf-8') as f:
        f.write(ps1.strip())


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
        self.geometry("800x700")
        self.resizable(False, False)
        self.iconbitmap(self.resource_path("aotr_fs.ico"))
        
        # Set custom cursor for the launcher window
        self.set_custom_cursor(self)

        # Selected folder and mod state
        self.install_folder = tk.StringVar()
        self.is_installed = False

        # Language selection
        self.language = tk.StringVar()
        self.language.set("english")  # Default language

        # Create background canvas
        self.create_background()

        # Layout Frames
        self.create_banner()
        self.create_top_buttons()
        self.create_news_section()
        self.create_bottom_section()

        # Load last folder and check mod version
        self.after(100, self.load_last_folder)

        # Check for updates for the launcher
        self.check_launcher_update()

    # ============ Auto-update (launcher) additions ============
    def _download_and_stage_zip(self, url: str) -> str:
        """
        Downloads and extracts the update ZIP to a temp staging folder.
        Returns the staging folder path that contains the new launcher files.
        """
        temp_root = tempfile.mkdtemp(prefix="realms_launcher_update_")
        zip_path = os.path.join(temp_root, "update.zip")

        # Download
        self.status_label.config(text="Downloading launcher update...", fg="blue")
        self.bg_canvas.itemconfig(self.progress_window, state="normal")
        self.progress["value"] = 0
        self.update()

        r = requests.get(url, stream=True)
        if r.status_code != 200:
            raise Exception(f"Unexpected status code: {r.status_code}")
        total = int(r.headers.get("content-length", 0))
        got = 0
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 14):
                if chunk:
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        self.progress["value"] = got * 100 / total
                    self.update()

        # Extract
        self.status_label.config(text="Staging launcher update...", fg="blue")
        self.update()
        staged_dir = os.path.join(temp_root, "staged")
        os.makedirs(staged_dir, exist_ok=True)
        with ZipFile(zip_path, "r") as zf:
            zf.extractall(staged_dir)

        # If the zip contains a top-level folder, descend into it so we copy *its* contents
        entries = list(pathlib.Path(staged_dir).iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            staged_dir = str(entries[0])

        # After extraction:
        try:
            with open(os.path.join(staged_dir, "_staged_ok.txt"), "w", encoding="utf-8") as f:
                f.write(f"staged at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception:
            pass

        return staged_dir

    def _quit_for_update(self):
        # Stop Tk event loop and exit so updater can replace files
        try:
            self.destroy()
        except:
            pass
        os._exit(0)

    # ==========================================================

    def check_admin_privileges(self):
        """Check if running with admin privileges and prompt user if not."""
        if not is_admin():
            result = messagebox.askyesno(
                "Admin Privileges Required",
                "This launcher requires administrator privileges to function properly.\n\n"
                "Would you like to restart the application with admin privileges?\n\n"
                "Note: This will close the current instance and restart with elevated permissions.",
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
            else:
                # User chose not to restart, show warning but continue
                messagebox.showwarning(
                    "Limited Functionality",
                    "The launcher will continue without admin privileges.\n"
                    "Some features may not work correctly.\n\n"
                    "To ensure full functionality, please run the launcher as administrator."
                )

    def resource_path(self, relative_path):
        """Get the absolute path to the resource, works for both dev and PyInstaller."""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def set_custom_cursor(self, widget):
        """Sets the custom cursor on a widget."""
        cursor_path = self.resource_path("SCCpointer.ico")
        if not os.path.exists(cursor_path):
            return
        
        # Try different cursor formats in order of preference
        abs_cursor_path = os.path.abspath(cursor_path)
        tk_cursor_path = abs_cursor_path.replace("\\", "/")
        
        # Method 1: Try @ prefix with forward slashes (Windows .cur/.ico format)
        try:
            widget.config(cursor=f"@{tk_cursor_path}")
            return
        except:
            pass
        
        # Method 2: Try @ prefix with backslashes
        try:
            widget.config(cursor=f"@{abs_cursor_path}")
            return
        except:
            pass
        
        # Method 3: Try without @ prefix (some Tkinter versions)
        try:
            widget.config(cursor=tk_cursor_path)
            return
        except:
            pass
        
        # Method 4: Try with just the filename (if in system path)
        try:
            cursor_filename = os.path.basename(cursor_path)
            widget.config(cursor=f"@{cursor_filename}")
            return
        except:
            pass
        
        # If all methods fail, print error but don't crash
        print(f"Warning: Could not set custom cursor from {cursor_path}")

    def create_background(self):
        """Creates a canvas with background image and fade effect."""
        try:
            # Create canvas for background
            self.bg_canvas = tk.Canvas(
                self, width=800, height=700, highlightthickness=0
            )
            self.bg_canvas.pack(fill="both", expand=True)
            
            # Set custom cursor for canvas
            self.set_custom_cursor(self.bg_canvas)

            # Load and resize background image
            bg_image = Image.open(self.resource_path("background.jpg"))
            bg_image = bg_image.resize((800, 700), Image.Resampling.LANCZOS)
            
            # Create fade overlay - darker at edges, lighter in center
            from PIL import ImageDraw
            fade_overlay = Image.new("RGBA", (800, 700), (0, 0, 0, 0))
            draw = ImageDraw.Draw(fade_overlay)
            
            # Create radial fade using ellipses for better performance
            center_x, center_y = 400, 350
            # Create multiple concentric ellipses for smooth gradient
            max_radius = 300
            for i in range(max_radius, 0, -2):
                alpha = int((1 - i/max_radius) ** 1.5 * 120)
                if alpha > 0:
                    # Draw ellipse with decreasing opacity
                    bbox = [
                        center_x - i, center_y - int(i * 0.8),
                        center_x + i, center_y + int(i * 0.8)
                    ]
                    # Use a semi-transparent black for the fade
                    draw.ellipse(bbox, fill=(0, 0, 0, alpha))
            
            # Composite the fade overlay onto the background
            bg_image = bg_image.convert("RGBA")
            bg_image = Image.alpha_composite(bg_image, fade_overlay)
            bg_image = bg_image.convert("RGB")
            
            self.bg_photo = ImageTk.PhotoImage(bg_image)

            # Place background image on canvas
            self.bg_canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)

            # Store reference to prevent garbage collection
            self.bg_canvas.bg_image = self.bg_photo
        except Exception as e:
            print(f"Error loading background: {e}")
            # Fallback: create a simple colored canvas
            self.bg_canvas = tk.Canvas(
                self, width=800, height=700, bg="#2b2b2b",
                highlightthickness=0
            )
            self.bg_canvas.pack(fill="both", expand=True)

    def draw_separator_border(self, x, y, width, height, tag="separator"):
        """Draws a separator border around a frame at given position."""
        # Top border
        self.bg_canvas.create_line(
            x - width//2, y - height//2 - 1,
            x + width//2, y - height//2 - 1,
            fill="#7f7f7f", width=2, tags=tag
        )
        self.bg_canvas.create_rectangle(
            x - width//2, y - height//2,
            x + width//2, y - height//2 + 1,
            fill="#5f5f5f", outline="", tags=tag
        )
        # Bottom border
        self.bg_canvas.create_rectangle(
            x - width//2, y + height//2 - 1,
            x + width//2, y + height//2,
            fill="#5f5f5f", outline="", tags=tag
        )
        self.bg_canvas.create_rectangle(
            x - width//2, y + height//2,
            x + width//2, y + height//2 + 2,
            fill="#1f1f1f", outline="", tags=tag
        )
        self.bg_canvas.create_rectangle(
            x - width//2, y + height//2 + 2,
            x + width//2, y + height//2 + 4,
            fill="#0f0f0f", outline="", tags=tag
        )
        # Left border
        self.bg_canvas.create_line(
            x - width//2 - 1, y - height//2,
            x - width//2 - 1, y + height//2,
            fill="#5f5f5f", width=2, tags=tag
        )
        # Right border
        self.bg_canvas.create_line(
            x + width//2 + 1, y - height//2,
            x + width//2 + 1, y + height//2,
            fill="#5f5f5f", width=2, tags=tag
        )

    def update_canvas_text(self, text_id, text=None, fg=None):
        """Updates a canvas text item's text and/or color."""
        if text is not None:
            self.bg_canvas.itemconfig(text_id, text=text)
        if fill is not None:
            self.bg_canvas.itemconfig(text_id, fg=fill)

    def style_button(
        self, button, bg_color="#4a90e2",
        hover_color="#357abd", text_color="white"
    ):
        """Styles a button with modern colors, border, shadow, and hover effects."""
        button.config(
            bg=bg_color,
            fg=text_color,
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            borderwidth=2,
            highlightthickness=0,
            padx=15,
            pady=8,
            cursor="hand2",
            activebackground=hover_color,
            activeforeground=text_color
        )

        # Add hover effects
        def on_enter(e):
            button.config(bg=hover_color, relief="raised")

        def on_leave(e):
            button.config(bg=bg_color, relief="raised")

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def add_button_shadow(self, window_id, offset_x=3, offset_y=3):
        """Adds a shadow effect behind a button window."""
        try:
            coords = self.bg_canvas.coords(window_id)
            if coords:
                x, y = coords
                # Get button bbox (approximate size)
                bbox = self.bg_canvas.bbox(window_id)
                if bbox:
                    x1, y1, x2, y2 = bbox
                    width = x2 - x1
                    height = y2 - y1
                    # Create shadow rectangle slightly offset and blurred
                    shadow_id = self.bg_canvas.create_rectangle(
                        x1 + offset_x, y1 + offset_y,
                        x2 + offset_x, y2 + offset_y,
                        fill="#000000", outline="", stipple="gray12"
                    )
                    # Move shadow behind button
                    self.bg_canvas.tag_lower(shadow_id, window_id)
                    return shadow_id
        except Exception:
            pass
        return None

    def add_button_glow(self, window_id, glow_color="#4a90e2", glow_size=20):
        """Adds a soft, diffused glow effect around a button window using multiple canvas ovals."""
        try:
            bbox = self.bg_canvas.bbox(window_id)
            if bbox:
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                width = x2 - x1
                height = y2 - y1
                
                glow_ids = []
                # Create multiple concentric ovals for smooth gradient glow
                num_layers = 10  # Number of glow layers
                
                print(f"Creating glow at center ({center_x}, {center_y}), button size: {width}x{height}")  # Debug
                
                for i in range(num_layers):
                    # Size increases from button edge outward
                    layer_size = (glow_size * i) / num_layers
                    # Opacity decreases from center outward
                    distance_ratio = i / num_layers
                    
                    # Calculate stipple pattern (gray0 = transparent, gray100 = opaque)
                    # Make it more visible - peak opacity in middle layers
                    if distance_ratio < 0.4:
                        # Fade in from button edge
                        stipple_value = int(60 + (distance_ratio / 0.4) * 25)  # 60 to 85
                    else:
                        # Fade out to transparent
                        stipple_value = int(85 - ((distance_ratio - 0.4) / 0.6) * 85)  # 85 to 0
                    
                    if stipple_value > 5:  # Only create if visible enough
                        # Create oval glow
                        oval_size = layer_size
                        glow_id = self.bg_canvas.create_oval(
                            center_x - width/2 - oval_size, 
                            center_y - height/2 - oval_size,
                            center_x + width/2 + oval_size, 
                            center_y + height/2 + oval_size,
                            fill=glow_color,
                            outline="",
                            stipple=f"gray{stipple_value}"  # Semi-transparent
                        )
                        glow_ids.append(glow_id)
                        # Move glow behind button
                        self.bg_canvas.tag_lower(glow_id, window_id)
                        print(f"Created glow layer {i}: size={oval_size:.1f}, stipple=gray{stipple_value}")  # Debug
                
                # Hide glow initially
                for glow_id in glow_ids:
                    self.bg_canvas.itemconfig(glow_id, state="hidden")
                
                return glow_ids
        except Exception as e:
            print(f"Error creating glow: {e}")
            import traceback
            traceback.print_exc()
        return []

    def create_banner(self):
        """Displays the banner at the top with separator."""
        try:
            image = Image.open(self.resource_path("banner.png"))
            image = image.resize((800, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            banner = tk.Label(self.bg_canvas, image=photo, bg="#000000", bd=0)
            banner.image = photo
            banner_window = self.bg_canvas.create_window(400, 75, window=banner)
            
            # Add prominent separator bar below banner (drawn after to appear on top)
            # Create a visible separator bar (10px tall with gradient effect)
            separator_y = 150
            # Bottom shadow for depth
            self.bg_canvas.create_rectangle(
                0, separator_y + 8, 800, separator_y + 10,
                fill="#000000", outline="", tags="separator"
            )
            # Dark base
            self.bg_canvas.create_rectangle(
                0, separator_y + 5, 800, separator_y + 8,
                fill="#0f0f0f", outline="", tags="separator"
            )
            # Main separator bar - darker and more visible
            self.bg_canvas.create_rectangle(
                0, separator_y + 2, 800, separator_y + 5,
                fill="#1f1f1f", outline="", tags="separator"
            )
            # Middle accent
            self.bg_canvas.create_rectangle(
                0, separator_y + 1, 800, separator_y + 2,
                fill="#3f3f3f", outline="", tags="separator"
            )
            # Top bright line for clear separation
            self.bg_canvas.create_rectangle(
                0, separator_y, 800, separator_y + 1,
                fill="#5f5f5f", outline="", tags="separator"
            )
            # Top highlight line
            self.bg_canvas.create_line(
                0, separator_y - 1, 800, separator_y - 1,
                fill="#7f7f7f", width=2, tags="separator"
            )
            
            # Ensure separator is above banner window
            self.bg_canvas.tag_raise("separator")
        except Exception as e:
            print(f"Error loading banner: {e}")

    def create_top_buttons(self):
        """Creates top buttons for folder selection, uninstallation."""
        # Place widgets directly on canvas to avoid frame backgrounds
        top_y = 200  # Increased from 180 to add more space below banner
        x_pos = 200  # Starting x position

        # Folder button
        self.folder_button = tk.Button(
            self.bg_canvas, text="Select Install Folder",
            command=self.select_folder
        )
        self.style_button(
            self.folder_button, bg_color="#4a90e2", hover_color="#357abd"
        )
        self.set_custom_cursor(self.folder_button)
        self.folder_button_window = self.bg_canvas.create_window(x_pos, top_y, window=self.folder_button)
        self.after(10, lambda: self.add_button_shadow(self.folder_button_window))
        Tooltip(self.folder_button, "Select AgeoftheRing folder.")
        x_pos += 150

        # Uninstall button
        self.uninstall_button = tk.Button(
            self.bg_canvas, text="Uninstall Mod",
            command=self.uninstall_mod, state="disabled"
        )
        self.style_button(
            self.uninstall_button, bg_color="#e74c3c", hover_color="#c0392b"
        )
        self.set_custom_cursor(self.uninstall_button)
        uninstall_window = self.bg_canvas.create_window(x_pos, top_y, window=self.uninstall_button)
        self.after(10, lambda: self.add_button_shadow(uninstall_window))
        Tooltip(
            self.uninstall_button,
            "Remove the mod and delete all its files and folders."
        )
        x_pos += 150

        # Create Shortcut button
        self.create_shortcut_button = tk.Button(
            self.bg_canvas, text="Create Shortcut",
            command=self.create_shortcut, state="disabled"
        )
        self.style_button(
            self.create_shortcut_button,
            bg_color="#95a5a6", hover_color="#7f8c8d"
        )
        self.set_custom_cursor(self.create_shortcut_button)
        shortcut_window = self.bg_canvas.create_window(x_pos, top_y, window=self.create_shortcut_button)
        self.after(10, lambda: self.add_button_shadow(shortcut_window))
        x_pos += 150

        # Language label - position above the dropdown
        language_x, language_y = x_pos, top_y - 25
        # Create shadow text first (behind main text)
        language_shadow = self.bg_canvas.create_text(
            language_x + 2, language_y + 2, text="Language:", fill="#000000",
            font=("Segoe UI", 9, "bold"), anchor="center"
        )
        # Create main text on top
        language_label = self.bg_canvas.create_text(
            language_x, language_y, text="Language:", fill="white",
            font=("Segoe UI", 9, "bold"), anchor="center"
        )
        # Ensure label is visible by raising it above other elements
        self.bg_canvas.tag_raise(language_label)

        # Language dropdown
        self.language_dropdown = ttk.Combobox(
            self.bg_canvas, textvariable=self.language,
            state="readonly", width=15
        )
        self.language_dropdown["values"] = ["English", "Portuguese (BR)"]
        self.language_dropdown.current(0)
        self.bg_canvas.create_window(x_pos, top_y, window=self.language_dropdown)
        self.language_dropdown.bind("<<ComboboxSelected>>", self.change_language)
        Tooltip(self.language_dropdown, "Change the language of the mod.")

    def create_news_section(self):
        """Creates the news section in the middle."""
        news_y = 350
        news_width = 780
        news_height = 200
        self.news_frame = tk.Frame(
            self.bg_canvas, borderwidth=0, relief="flat",
            height=news_height, width=news_width, bg="#1a1a1a"
        )
        self.news_frame.pack_propagate(False)
        self.set_custom_cursor(self.news_frame)
        self.bg_canvas.create_window(400, news_y, window=self.news_frame)
        
        # Draw separator border around news section
        self.draw_separator_border(400, news_y, news_width, news_height, "news_sep")

        news_title = tk.Label(
            self.news_frame, text="Latest News",
            font=("Segoe UI", 12, "bold"), bg="#1a1a1a", fg="white"
        )
        news_title.pack(pady=5)
        self.news_label = HTMLLabel(self.news_frame, html=self.fetch_news())
        self.news_label.pack(fill="both", expand=True, padx=5, pady=5)

    def create_bottom_section(self):
        """Creates the bottom section for Download button."""
        bottom_y = 550

        # Bottom info - create frame with black background like news container
        info_y = 680
        info_width = 780
        info_height = 30

        # Play Button - place directly on canvas
        # Load icon for the button
        try:
            icon_image = Image.open(self.resource_path("icons8-one-ring-96.png"))
            icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
            self.play_button_icon = ImageTk.PhotoImage(icon_image)
        except Exception as e:
            print(f"Error loading play button icon: {e}")
            self.play_button_icon = None
        
        self.play_button = tk.Button(
            self.bg_canvas,
            text="Play",
            image=self.play_button_icon if self.play_button_icon else None,
            compound="left" if self.play_button_icon else None,
            command=self.launch_game
        )
        # Store reference to prevent garbage collection
        if self.play_button_icon:
            self.play_button.image = self.play_button_icon
        
        self.style_button(
            self.play_button, bg_color="#27ae60", hover_color="#229954"
        )
        # Set larger font and fixed size for Play Mod button (after style_button to override default)
        # Use padx/pady for fixed pixel size instead of width/height which scales with font
        # Adjust padding to center text: use single padx value (Tkinter doesn't support tuple in config)
        self.play_button.config(
            font=("Segoe UI", 18, "bold"),
            padx=30,  # Horizontal padding
            pady=15,
            anchor="center",
            justify="center"
        )
        # Set custom cursor on the button to prevent it from changing on hover
        # Do this after all config to ensure it's not overridden
        self.set_custom_cursor(self.play_button)
        # Shadow will be added when button is shown

        # Download Button - place directly on canvas
        self.download_button = tk.Button(
            self.bg_canvas,
            text="Checking...",
            state="disabled",

            command=self.download_and_extract_mod
        )
        self.style_button(
            self.download_button,
            bg_color="#27ae60", hover_color="#229954"
        )
        self.set_custom_cursor(self.download_button)
        self.download_button_window = self.bg_canvas.create_window(
            400, bottom_y, window=self.download_button
        )
        self.after(10, lambda: self.add_button_shadow(self.download_button_window))

        # Progress Bar - place directly on canvas
        self.progress = ttk.Progressbar(
            self.bg_canvas, orient="horizontal",
            length=500, mode="determinate"
        )
        self.progress_window = self.bg_canvas.create_window(
            400, bottom_y + 40, window=self.progress
        )
        self.bg_canvas.itemconfig(self.progress_window, state="hidden")

        # Create frame with black background
        self.info_frame = tk.Frame(
            self.bg_canvas, borderwidth=0, relief="flat",
            height=info_height, width=info_width, bg="#000000"
        )
        self.info_frame.pack_propagate(False)
        self.set_custom_cursor(self.info_frame)
        self.bg_canvas.create_window(400, info_y, window=self.info_frame)
        
        # Draw separator border around bottom info frame
        self.draw_separator_border(400, info_y, info_width, info_height, "info_sep")

        # Folder Label (left) - place in frame
        self.folder_label = tk.Label(
            self.info_frame,
            text="Installation Folder: Not selected",
            font=("Segoe UI", 9),
            anchor="w",
            fg="white",
            bg="#000000"
        )
        self.folder_label.pack(side="left", padx=10, pady=5)

        # Status Label (center) - centered relative to entire screen width (400px)
        self.status_label = tk.Label(
            self.info_frame,
            text="Checking mod status...",
            font=("Segoe UI", 9, "bold"),
            anchor="center",
            fg="#4a90e2",
            bg="#000000"
        )
        # Place at screen center (400px from screen left)
        # Frame is 780px wide, centered at 400px, so frame left is at 10px
        # Screen center (400px) - frame left (10px) = 390px from frame left
        self.status_label.place(x=390, rely=0.5, anchor="center")

        # Launcher Version Label (right) - place in frame
        self.version_label = tk.Label(
            self.info_frame,
            text=f"Launcher v{LAUNCHER_VERSION}",
            font=("Segoe UI", 9),
            anchor="e",
            fg="white",
            bg="#000000"
        )
        self.version_label.pack(side="right", padx=10, pady=5)

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
        self.folder_label.config(text="Installation Folder: Not selected")
        self.hide_download_button()
        self.hide_play_button()
        self.uninstall_button.config(state="disabled")
        self.create_shortcut_button.config(state="disabled")
        self.language_dropdown.config(state="disabled")

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
                    "Please select the correct Age of the Ring folder that contains the 'aotr' subfolder."
                )
                self.update_canvas_text(
                    self.status_label,
                    text="Please select the correct Age of the Ring folder.",
                    fill="red"
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
            self.hide_play_button()

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
                    self.hide_play_button()
                    self.uninstall_button.config(state="disabled")
                    self.show_folder_button()
                    self.language_dropdown.config(state="disabled")
                elif local_version != remote_version:
                    self.update_canvas_text(
                        self.status_label,
                        text=f"Update available: {remote_version} (Installed: {local_version})",
                        fill="orange"
                    )
                    self.download_button.config(text="Download Update", state="normal")
                    self.show_download_button()
                    self.show_play_button()
                    self.uninstall_button.config(state="normal")
                    self.create_shortcut_button.config(state="normal")
                    self.hide_folder_button()
                    self.language_dropdown.config(state="readonly")
                else:
                    self.status_label.config(text=f"Mod is up-to-date ({local_version}).", fg="green")
                    self.hide_download_button()
                    self.show_play_button()
                    self.uninstall_button.config(state="normal")
                    self.create_shortcut_button.config(state="normal")
                    self.hide_folder_button()
                    self.language_dropdown.config(state="readonly")
            else:
                self.status_label.config(text="Failed to check for updates.", fg="red")
                self.download_button.config(text="Retry", state="normal")
                self.show_download_button()
                self.hide_play_button()
                self.uninstall_button.config(state="disabled")
                self.create_shortcut_button.config(state="disabled")
                self.language_dropdown.config(state="disabled")

        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.download_button.config(text="Retry", state="normal")
            self.show_download_button()
            self.hide_play_button()
            self.uninstall_button.config(state="disabled")
            self.create_shortcut_button.config(state="disabled")
            self.language_dropdown.config(state="disabled")

    def show_download_button(self):
        """Show the download button."""
        self.bg_canvas.itemconfig(self.download_button_window, state="normal")

    def hide_download_button(self):
        """Hide the download button."""
        self.bg_canvas.itemconfig(self.download_button_window, state="hidden")

    def show_play_button(self):
        """Show the play button."""
        if not hasattr(self, 'play_button_window'):
            # Position button at bottom_y (550), status label is at bottom_y - 70 (480)
            self.play_button_window = self.bg_canvas.create_window(
                400, 550, window=self.play_button, anchor="center"
            )
            # Add shadow effect
            self.after(10, lambda: self.add_button_shadow(self.play_button_window))
            # Add glow effect for hover
            self.after(20, lambda: self._setup_play_button_glow())
        self.bg_canvas.itemconfig(self.play_button_window, state="normal")

    def _setup_play_button_glow(self):
        """Sets up the glow effect for the play button and hover handlers."""
        if hasattr(self, 'play_button_window'):
            # Create glow effect (green to match button, larger and more visible)
            self.play_button_glow_ids = self.add_button_glow(
                self.play_button_window, glow_color="#2ecc71", glow_size=25  # Brighter green, larger size
            )
            
            # Add hover handlers to show/hide glow
            def on_enter(e):
                print("Hover ENTER detected")  # Debug
                if hasattr(self, 'play_button_glow_ids') and self.play_button_glow_ids:
                    print(f"Showing glow: {self.play_button_glow_ids}")  # Debug
                    for glow_id in self.play_button_glow_ids:
                        self.bg_canvas.itemconfig(glow_id, state="normal")
                    # Force canvas update
                    self.bg_canvas.update_idletasks()
                else:
                    print("No glow IDs available")  # Debug
            
            def on_leave(e):
                print("Hover LEAVE detected")  # Debug
                if hasattr(self, 'play_button_glow_ids') and self.play_button_glow_ids:
                    for glow_id in self.play_button_glow_ids:
                        self.bg_canvas.itemconfig(glow_id, state="hidden")
                    # Force canvas update
                    self.bg_canvas.update_idletasks()
            
            # Bind to the button widget for hover detection
            self.play_button.bind("<Enter>", on_enter)
            self.play_button.bind("<Leave>", on_leave)
            # Also try binding to Motion events
            self.play_button.bind("<Motion>", lambda e: on_enter(e))
            
            # Debug: Print if glow was created
            if self.play_button_glow_ids:
                print(f"Glow created with {len(self.play_button_glow_ids)} items, IDs: {self.play_button_glow_ids}")
                # Test: Temporarily show glow to verify it's visible
                print("Testing glow visibility - showing for 2 seconds...")
                for glow_id in self.play_button_glow_ids:
                    self.bg_canvas.itemconfig(glow_id, state="normal")
                self.after(2000, lambda: [self.bg_canvas.itemconfig(glow_id, state="hidden") for glow_id in self.play_button_glow_ids])
            else:
                print("Warning: No glow items created")

    def hide_play_button(self):
        """Hide the play button."""
        if hasattr(self, 'play_button_window'):
            self.bg_canvas.itemconfig(self.play_button_window, state="hidden")
            # Also hide glow if it exists
            if hasattr(self, 'play_button_glow_ids'):
                for glow_id in self.play_button_glow_ids:
                    self.bg_canvas.itemconfig(glow_id, state="hidden")

    def show_folder_button(self):
        """Show the folder button."""
        if hasattr(self, 'folder_button_window'):
            self.bg_canvas.itemconfig(self.folder_button_window, state="normal")

    def hide_folder_button(self):
        """Hide the folder button."""
        if hasattr(self, 'folder_button_window'):
            self.bg_canvas.itemconfig(self.folder_button_window, state="hidden")

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
            self.hide_folder_button()

            # Hide the Download button during the download process
            self.hide_download_button()
            self.hide_play_button()
            self.bg_canvas.itemconfig(self.progress_window, state="normal")

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

            # Only prepare realms folder (copy from aotr) if this is a base install
            if not os.path.exists(version_file) or needs_base_first:
                if not aotr_updated:
                    realms_folder = self.prepare_realms_folder(install_path)
            # For updates, do not recreate realms folder, just use the existing one
            # Ensure realms folder exists before proceeding
            if not os.path.exists(realms_folder) or not os.path.isdir(realms_folder):
                raise Exception("Realms folder not found. AOTR extraction failed and no fallback available.")

            # First install base version if needed
            if needs_base_first:
                self.status_label.config(text=f"Installing base version {BASE_MOD_VERSION}...", fg="blue")
                self.update()

                # Download and install base version
                self.download_and_install_package(realms_folder, BASE_MOD_ZIP_URL, "base mod", BASE_MOD_VERSION)

                # Update local version to base version
                with open(version_file, "w") as file:
                    json.dump({"version": BASE_MOD_VERSION}, file)

                # Now update to remote if needed
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
            self.uninstall_button.config(state="normal")
            self.bg_canvas.itemconfig(self.progress_window, state="hidden")
            self.save_folder(install_path, installed=True)

            # Re-enable folder selection
            self.show_folder_button()

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
            self.bg_canvas.itemconfig(self.progress_window, state="hidden")
            self.show_download_button()
            self.hide_play_button()

            # Re-enable folder selection on error
            self.show_folder_button()

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
                    self.progress["value"] = (downloaded_size / total_size) * 100 if total_size else 0
                    self.update()

        # Update status during installation
        self.status_label.config(text=f"Installing {version_label}...", fg="blue")
        self.update()

        # Extract the ZIP file to a temporary location to handle nested structure
        temp_dir = os.path.join(parent_dir, "temp_extraction")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        try:
            # Extract the ZIP file to temporary location
            with ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find the realms folder in the extracted structure
            realms_folder_found = None
            for root, dirs, files in os.walk(temp_dir):
                if "realms" in dirs:
                    realms_folder_found = os.path.join(root, "realms")
                    break

            if realms_folder_found:
                # Ensure the target directory exists
                if not os.path.exists(install_path):
                    os.makedirs(install_path)

                # Extract each file from the found realms folder to the target location
                self.status_label.config(text="Installing realms folder...", fg="blue")
                self.update()

                for root, dirs, files in os.walk(realms_folder_found):
                    # Calculate the relative path from the realms folder
                    rel_path = os.path.relpath(root, realms_folder_found)
                    target_dir = os.path.join(install_path, rel_path)

                    # Create target directory if it doesn't exist
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)

                    # Copy files to target location (overwrite existing files)
                    for file in files:
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(target_dir, file)
                        shutil.copy2(src_file, dst_file)

            else:
                # Fallback: extract directly to parent directory (old behavior)
                self.status_label.config(text="Using fallback extraction method...", fg="blue")
                self.update()
                with ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(parent_dir)

        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        # Remove the downloaded ZIP file
        try:
            os.remove(zip_path)
        except Exception:
            pass

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
                    self.update_canvas_text(
                        self.status_label,
                        text="Found existing AOTR RAR file. Extracting...",
                        fill="blue"
                    )
                    self.update()
                    return True, existing_rar_path
                else:
                    self.update_canvas_text(
                        self.status_label,
                        text=f"Realms in Exile requires AOTR {required_version}. "
                             f"Current version: {current_version}. Downloading...",
                        fill="blue"
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

            # Copy dxvk.conf from realms/dxvk/ to rotwk/ if it exists
            dxvk_source = os.path.join(mod_folder, "dxvk", "dxvk.conf")
            dxvk_dest = os.path.join(rotwk_folder, "dxvk.conf")

            if os.path.exists(dxvk_source):
                try:
                    shutil.copy2(dxvk_source, dxvk_dest)
                    print(f"Copied dxvk.conf from {dxvk_source} to {dxvk_dest}")
                except Exception as e:
                    print(f"Warning: Failed to copy dxvk.conf: {e}")
            else:
                print("dxvk.conf not found in realms/dxvk/, skipping copy")

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

                for file in os.listdir(desktop):
                    if re.match(rf"Realms in Exile v.*\.lnk", file):  # Match all versions
                        shortcut_path = os.path.join(desktop, file)
                        os.remove(shortcut_path)  # Delete the shortcut
                        print(f"Deleted shortcut: {shortcut_path}")

                # Reset UI and clear registry
                self.update_canvas_text(
                    self.status_label,
                    text="Mod uninstalled successfully. All files and folders were removed.",
                    fill="green"
                )
                self.folder_label.config(text="Installation Folder: Not selected")
                self.install_folder.set("")
                self.save_folder("", installed=False)

                # Update UI elements
                self.hide_download_button()
                self.hide_play_button()
                self.uninstall_button.config(state="disabled")
                self.create_shortcut_button.config(state="disabled")
                self.show_folder_button()
                self.language_dropdown.config(state="disabled")

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
                        f"A new launcher version ({latest_launcher_version}) is available. Download and apply now?"
                    )
                    if user_choice:
                        self.update_launcher()
                else:
                    print(f"Launcher is up-to-date ({LAUNCHER_VERSION}).")
            else:
                messagebox.showerror("Update Check Failed", "Failed to fetch version.json.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check for launcher updates: {e}")

    def update_launcher(self):
        """
        Auto-updates the launcher:
        1) download + extract to temp
        2) spawn updater (PowerShell) that waits for us to exit
        3) updater mirrors files into our launcher folder
        4) updater relaunches the launcher
        5) logs everything to log.txt (in the launcher folder)
        """
        try:
            self.enter_update_mode()
            self.status_label.config(text="Preparing launcher update...", fg="blue")
            self.update()

            # 1) Stage the ZIP
            staged_dir = self._download_and_stage_zip(LAUNCHER_ZIP_URL)

            # 2) Write updater script
            temp_root = os.path.dirname(os.path.dirname(staged_dir))  # parent of 'staged'
            ps1_path = os.path.join(temp_root, "do_update.ps1")
            _write_updater_ps1(ps1_path)

            # Path for target
            target_dir = _launcher_dir()

            # ALWAYS write logs to %TEMP% (writable even without elevation)
            log_path = os.path.join(tempfile.gettempdir(), "realms_launcher_update.log")

            # Pre-create & stamp the log so we know Python got this far
            try:
                with open(log_path, "a", encoding="utf-8") as lf:
                    lf.write(f"[python] starting update at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            except Exception as e:
                messagebox.showerror("Logging", f"Couldn't open log file:\n{log_path}\n{e}")

            if _is_frozen():
                relaunch_path = _launcher_path()     # the updated .exe
                relaunch_args = ""                   # none
            else:
                # Relaunch the same script with the same interpreter
                relaunch_path = sys.executable
                relaunch_args = f'"{os.path.abspath(sys.argv[0])}"'

            relaunch_cwd = target_dir  # important for relative assets

            # 3) Build PowerShell argument list
            base_args = [
                "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", ps1_path,
                "-TargetDir", target_dir,
                "-StagedDir", staged_dir,
                "-MainPid", str(os.getpid()),
                "-RelaunchPath", relaunch_path,
                "-RelaunchArgs", relaunch_args,
                "-RelaunchCwd", relaunch_cwd,
                "-LogPath", log_path,
            ]

            # 4) Launch updater (optionally elevated)
            if USE_ELEVATED_UPDATER:
                # When elevating with ShellExecute, we must pass a single string of args
                def _join_ps_args(args):
                    out = []
                    for a in args:
                        if a is None:
                            continue
                        # Quote only when needed
                        if (' ' in a or '"' in a) and not a.startswith('-'):
                            a = '"' + a.replace('"', '""') + '"'
                        out.append(a)
                    return " ".join(out)

                arg_string = _join_ps_args(base_args)
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "powershell.exe", arg_string, None, 1
                )
            else:
                _start_detached(["powershell.exe"] + base_args)

            # 5) Inform and quit so the updater can replace files
            self.status_label.config(text="Applying update... The launcher will close and reopen.", fg="blue")
            self.update()
            self.after(300, self._quit_for_update)

        except Exception as e:
            messagebox.showerror("Update Failed", f"Failed to update the launcher: {e}")
            self.bg_canvas.itemconfig(self.progress_window, state="hidden")
            self.exit_update_mode()

    def is_newer_version(self, current_version, latest_version):
        """Return True if latest_version > current_version (numeric compare)."""
        try:
            current_parts = list(map(int, current_version.split(".")))
            latest_parts = list(map(int, latest_version.split(".")))
            # Pad arrays to equal length
            L = max(len(current_parts), len(latest_parts))
            current_parts += [0] * (L - len(current_parts))
            latest_parts += [0] * (L - len(latest_parts))
            return latest_parts > current_parts
        except ValueError:
            return False
        
    def enter_update_mode(self):
        self.is_updating = True
        self.hide_play_button()
        # lock UI so the user can't trigger other actions mid-update
        for w in (self.folder_button, self.uninstall_button, self.language_dropdown):
            try:
                w.config(state="disabled")
            except Exception:
                pass
        try:
            self.download_button.config(state="disabled")
        except Exception:
            pass
        # show progress bar if not visible
        try:
            self.bg_canvas.itemconfig(self.progress_window, state="normal")
        except Exception:
            pass

    def exit_update_mode(self):
        # Only used if update failed; on success we quit the app.
        self.is_updating = False
        # restore controls (Play may stay hidden if you prefer; here we restore it)
        try:
            self.show_play_button()
        except Exception:
            pass
        for w in (self.folder_button, self.uninstall_button, self.language_dropdown):
            try:
                # folder_button normally disabled after install checks; safest is "normal"
                w.config(state="normal")
            except Exception:
                pass
        try:
            self.download_button.config(state="normal")
        except Exception:
            pass
        try:
            self.bg_canvas.itemconfig(self.progress_window, state="hidden")
        except Exception:
            pass

if __name__ == "__main__":
    app = ModLauncher()
    app.mainloop()
