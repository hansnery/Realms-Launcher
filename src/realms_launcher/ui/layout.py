from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk
from tkhtmlview import HTMLLabel

from ..constants import LAUNCHER_VERSION


def create_background(self) -> None:
    """Creates a canvas with background image and fade effect."""
    try:
        self.bg_canvas = tk.Canvas(self, width=800, height=700, highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)

        self.set_custom_cursor(self.bg_canvas)

        bg_image = Image.open(self.resource_path("background.jpg"))
        bg_image = bg_image.resize((800, 700), Image.Resampling.LANCZOS)

        from PIL import ImageDraw

        fade_overlay = Image.new("RGBA", (800, 700), (0, 0, 0, 0))
        draw = ImageDraw.Draw(fade_overlay)

        center_x, center_y = 400, 350
        max_radius = 300
        for i in range(max_radius, 0, -2):
            alpha = int((1 - i / max_radius) ** 1.5 * 120)
            if alpha > 0:
                bbox = [
                    center_x - i,
                    center_y - int(i * 0.8),
                    center_x + i,
                    center_y + int(i * 0.8),
                ]
                draw.ellipse(bbox, fill=(0, 0, 0, alpha))

        bg_image = bg_image.convert("RGBA")
        bg_image = Image.alpha_composite(bg_image, fade_overlay)
        bg_image = bg_image.convert("RGB")

        self.bg_photo = ImageTk.PhotoImage(bg_image)
        self.bg_canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)
        self.bg_canvas.bg_image = self.bg_photo
    except Exception as e:
        print(f"Error loading background: {e}")
        self.bg_canvas = tk.Canvas(self, width=800, height=700, bg="#2b2b2b", highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)


def create_banner(self) -> None:
    """Displays the banner at the top with separator."""
    try:
        image = Image.open(self.resource_path("banner.png"))
        image = image.resize((800, 150), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        banner = tk.Label(self.bg_canvas, image=photo, bg="#000000", bd=0)
        banner.image = photo
        self.bg_canvas.create_window(400, 75, window=banner)

        separator_y = 150
        self.bg_canvas.create_rectangle(0, separator_y + 8, 800, separator_y + 10, fill="#000000", outline="", tags="separator")
        self.bg_canvas.create_rectangle(0, separator_y + 5, 800, separator_y + 8, fill="#0f0f0f", outline="", tags="separator")
        self.bg_canvas.create_rectangle(0, separator_y + 2, 800, separator_y + 5, fill="#1f1f1f", outline="", tags="separator")
        self.bg_canvas.create_rectangle(0, separator_y + 1, 800, separator_y + 2, fill="#3f3f3f", outline="", tags="separator")
        self.bg_canvas.create_rectangle(0, separator_y, 800, separator_y + 1, fill="#5f5f5f", outline="", tags="separator")
        self.bg_canvas.create_line(0, separator_y - 1, 800, separator_y - 1, fill="#7f7f7f", width=2, tags="separator")

        self.bg_canvas.tag_raise("separator")
    except Exception as e:
        print(f"Error loading banner: {e}")


def create_top_buttons(self) -> None:
    """Creates top buttons for folder selection, uninstallation."""
    top_y = 200
    x_pos = 200

    self.folder_button = tk.Button(self.bg_canvas, text="Select Install Folder", command=self.select_folder)
    self.style_button(self.folder_button, bg_color="#4a90e2", hover_color="#357abd")
    self.set_custom_cursor(self.folder_button)
    self.folder_button_window = self.bg_canvas.create_window(x_pos, top_y, window=self.folder_button)
    self.after(10, lambda: self.add_button_shadow(self.folder_button_window))
    x_pos += 150

    self.create_shortcut_button = tk.Button(
        self.bg_canvas, text="Create Shortcut", command=self.create_shortcut, state="disabled"
    )
    self.style_button(self.create_shortcut_button, bg_color="#4a90e2", hover_color="#357abd")
    self.set_custom_cursor(self.create_shortcut_button)
    self.create_shortcut_button_window = self.bg_canvas.create_window(x_pos, top_y, window=self.create_shortcut_button)
    self.after(10, lambda: self.add_button_shadow(self.create_shortcut_button_window))
    x_pos += 150

    self.uninstall_button = tk.Button(
        self.bg_canvas, text="Uninstall Mod", command=self.uninstall_mod, state="disabled"
    )
    self.style_button(self.uninstall_button, bg_color="#e74c3c", hover_color="#c0392b")
    self.set_custom_cursor(self.uninstall_button)
    self.uninstall_button_window = self.bg_canvas.create_window(x_pos, top_y, window=self.uninstall_button)
    self.after(10, lambda: self.add_button_shadow(self.uninstall_button_window))

    self.hide_uninstall_button()
    self.hide_create_shortcut_button()
    self.after(50, self._update_folder_button_position)
    x_pos += 150

    language_x, language_y = x_pos, top_y - 25
    self.bg_canvas.create_text(
        language_x + 2, language_y + 2, text="Language:", fill="#000000", font=("Segoe UI", 9, "bold"), anchor="center"
    )
    language_label = self.bg_canvas.create_text(
        language_x, language_y, text="Language:", fill="white", font=("Segoe UI", 9, "bold"), anchor="center"
    )
    self.bg_canvas.tag_raise(language_label)

    self.language_dropdown = ttk.Combobox(self.bg_canvas, textvariable=self.language, state="readonly", width=15)
    self.language_dropdown["values"] = ["English", "Portuguese (BR)"]
    self.language_dropdown.current(0)
    self.bg_canvas.create_window(x_pos, top_y, window=self.language_dropdown)
    self.language_dropdown.bind("<<ComboboxSelected>>", self.change_language)


def create_news_section(self) -> None:
    """Creates the news section in the middle."""
    news_y = 350
    news_width = 780
    news_height = 200
    self.news_frame = tk.Frame(
        self.bg_canvas, borderwidth=0, relief="flat", height=news_height, width=news_width, bg="#1a1a1a"
    )
    self.news_frame.pack_propagate(False)
    self.set_custom_cursor(self.news_frame)
    self.bg_canvas.create_window(400, news_y, window=self.news_frame)

    self.draw_separator_border(400, news_y, news_width, news_height, "news_sep")

    news_title = tk.Label(
        self.news_frame, text="Latest News", font=("Segoe UI", 12, "bold"), bg="#1a1a1a", fg="white"
    )
    news_title.pack(pady=5)

    news_html = self.fetch_news()
    try:
        self.news_label = HTMLLabel(self.news_frame, html=news_html)
        self.news_label.pack(fill="both", expand=True, padx=5, pady=5)
    except Exception as e:
        print(f"HTML parsing error in news widget: {e}")
        self.news_label = tk.Label(
            self.news_frame,
            text="Failed to load news. Please check your internet connection.",
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#000000",
            wraplength=600,
            justify="left",
        )
        self.news_label.pack(fill="both", expand=True, padx=5, pady=5)


def create_bottom_section(self) -> None:
    """Creates the bottom section (Play/Download + progress + footer)."""
    bottom_y = 550

    info_y = 680
    info_width = 780
    info_height = 30

    # Play Button
    ani_path = self.resource_path("OneRing.ani")
    self.play_button_frames = None
    self.play_button_delays = None
    self.play_button_icon = None

    if os.path.exists(ani_path):
        try:
            frames, delays = self.load_ani_frames(ani_path, target_size=(32, 32))
            if frames:
                self.play_button_frames = frames
                self.play_button_delays = delays
                self.play_button_icon = frames[0]
            else:
                self.play_button_icon = None
        except Exception as e:
            print(f"Error loading animated icon: {e}")
            self.play_button_icon = None

    if not self.play_button_icon:
        try:
            icon_image = Image.open(self.resource_path("icons8-one-ring-96.png"))
            icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
            self.play_button_icon = ImageTk.PhotoImage(icon_image)
        except Exception as e:
            print(f"Error loading play button icon: {e}")
            self.play_button_icon = None

    self.play_button = tk.Button(
        self.bg_canvas,
        text="Play Realms in Exile",
        image=self.play_button_icon if self.play_button_icon else None,
        compound="left" if self.play_button_icon else None,
        command=self.launch_game,
    )
    if self.play_button_icon:
        self.play_button.image = self.play_button_icon
    if self.play_button_frames:
        self.animate_button_icon(self.play_button, self.play_button_frames, self.play_button_delays)

    self.style_button(self.play_button, bg_color="#27ae60", hover_color="#229954")
    self.play_button_font = self.load_custom_font("ringbearer/RINGM___.TTF", size=16)
    self.play_button.config(
        font=self.play_button_font,
        fg="white",
        padx=30,
        pady=30,
        anchor="center",
        justify="center",
        height=5,
    )
    self.set_custom_cursor(self.play_button)

    # Download Button (icons: repair/update/checking)
    repair_ani_path = self.resource_path("SCCRepair.ani")
    attmagic_ani_path = self.resource_path("SCCAttMagic.ani")
    magnify_ani_path = self.resource_path("magnify.ani")

    self.download_button_frames = None
    self.download_button_delays = None
    self.download_button_icon = None
    if os.path.exists(repair_ani_path):
        try:
            frames, delays = self.load_ani_frames(repair_ani_path, target_size=(32, 32))
            if frames:
                self.download_button_frames = frames
                self.download_button_delays = delays
                self.download_button_icon = frames[0]
        except Exception as e:
            print(f"Error loading download button animated icon: {e}")

    self.update_button_frames = None
    self.update_button_delays = None
    self.update_button_icon = None
    if os.path.exists(attmagic_ani_path):
        try:
            frames, delays = self.load_ani_frames(attmagic_ani_path, target_size=(32, 32))
            if frames:
                self.update_button_frames = frames
                self.update_button_delays = delays
                self.update_button_icon = frames[0]
        except Exception as e:
            print(f"Error loading update button animated icon: {e}")

    self.checking_button_frames = None
    self.checking_button_delays = None
    self.checking_button_icon = None
    if os.path.exists(magnify_ani_path):
        try:
            frames, delays = self.load_ani_frames(magnify_ani_path, target_size=(32, 32))
            if frames:
                self.checking_button_frames = frames
                self.checking_button_delays = delays
                self.checking_button_icon = frames[0]
        except Exception as e:
            print(f"Error loading checking button animated icon: {e}")

    initial_icon = self.checking_button_icon if self.checking_button_icon else self.download_button_icon
    self.download_button = tk.Button(
        self.bg_canvas,
        text="Checking...",
        state="disabled",
        image=initial_icon if initial_icon else None,
        compound="left" if initial_icon else None,
        command=self.download_and_extract_mod,
    )
    if initial_icon:
        self.download_button.image = initial_icon

    if self.checking_button_frames:
        self.animate_button_icon(self.download_button, self.checking_button_frames, self.checking_button_delays)
    elif self.download_button_frames:
        self.animate_button_icon(self.download_button, self.download_button_frames, self.download_button_delays)

    self.style_button(self.download_button, bg_color="#27ae60", hover_color="#229954")
    self.download_button_font = self.load_custom_font("ringbearer/RINGM___.TTF", size=16)
    self.download_button.config(
        font=self.download_button_font,
        fg="white",
        padx=30,
        pady=30,
        anchor="center",
        justify="center",
        height=5,
    )
    self.set_custom_cursor(self.download_button)

    # Place buttons and progress
    self.play_button_window = self.bg_canvas.create_window(400, bottom_y - 60, window=self.play_button)
    self.after(10, lambda: self.add_button_shadow(self.play_button_window))
    self.hide_play_button()

    self.download_button_window = self.bg_canvas.create_window(400, bottom_y - 5, window=self.download_button)
    self.after(10, lambda: self.add_button_shadow(self.download_button_window))

    self.progress = ttk.Progressbar(self.bg_canvas, orient="horizontal", length=500, mode="determinate")
    self.progress_window = self.bg_canvas.create_window(400, bottom_y + 40, window=self.progress)
    self.bg_canvas.itemconfig(self.progress_window, state="hidden")

    # Footer info frame
    self.info_frame = tk.Frame(self.bg_canvas, borderwidth=0, relief="flat", height=info_height, width=info_width, bg="#000000")
    self.info_frame.pack_propagate(False)
    self.set_custom_cursor(self.info_frame)
    self.bg_canvas.create_window(400, info_y, window=self.info_frame)

    self.draw_separator_border(400, info_y, info_width, info_height, "info_sep")

    self.folder_label = tk.Label(
        self.info_frame,
        text="Installation Folder: Not selected",
        font=("Segoe UI", 9),
        anchor="w",
        fg="white",
        bg="#000000",
    )
    self.folder_label.pack(side="left", padx=10, pady=5)

    self.status_label = tk.Label(
        self.info_frame,
        text="Checking mod status...",
        font=("Segoe UI", 9, "bold"),
        anchor="center",
        fg="#4a90e2",
        bg="#000000",
    )
    self.status_label.place(x=390, rely=0.5, anchor="center")

    self.version_label = tk.Label(
        self.info_frame,
        text=f"Launcher v{LAUNCHER_VERSION}",
        font=("Segoe UI", 9),
        anchor="e",
        fg="white",
        bg="#000000",
    )
    self.version_label.pack(side="right", padx=10, pady=5)

