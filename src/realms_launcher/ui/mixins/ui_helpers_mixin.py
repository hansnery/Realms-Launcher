from __future__ import annotations

import os
from tkinter import font as tkfont

from .. import cursors as ui_cursors
from .. import effects as ui_effects
from .. import layout as ui_layout
from ..ani import load_ani_frames as ui_load_ani_frames
from ..assets import resource_path as resolve_resource_path


class UiHelpersMixin:
    """Small UI-only wrappers that delegate to helper modules."""

    def update_download_button_icon(self, button_text: str) -> None:
        """Update the download button icon based on current state text."""
        if not hasattr(self, "download_button"):
            return

        # Stop any existing animation by clearing the animation ID
        if hasattr(self, "_download_button_animation_id"):
            try:
                self.after_cancel(self._download_button_animation_id)  # type: ignore[attr-defined]
                delattr(self, "_download_button_animation_id")
            except Exception:
                pass

        # Determine which icon to use based on button text
        if button_text == "Checking...":
            if getattr(self, "checking_button_icon", None) and getattr(
                self, "checking_button_frames", None
            ):
                self.download_button.config(image=self.checking_button_icon)  # type: ignore[attr-defined]
                self.download_button.image = self.checking_button_icon  # type: ignore[attr-defined]
                self.animate_button_icon(
                    self.download_button,  # type: ignore[attr-defined]
                    self.checking_button_frames,
                    self.checking_button_delays,
                )
            else:
                self.download_button.config(image="")  # type: ignore[attr-defined]
        elif "Update" in button_text:
            if getattr(self, "update_button_icon", None) and getattr(
                self, "update_button_frames", None
            ):
                self.download_button.config(image=self.update_button_icon)  # type: ignore[attr-defined]
                self.download_button.image = self.update_button_icon  # type: ignore[attr-defined]
                self.animate_button_icon(
                    self.download_button,  # type: ignore[attr-defined]
                    self.update_button_frames,
                    self.update_button_delays,
                )
            else:
                self.download_button.config(image="")  # type: ignore[attr-defined]
        else:
            if getattr(self, "download_button_icon", None) and getattr(
                self, "download_button_frames", None
            ):
                self.download_button.config(image=self.download_button_icon)  # type: ignore[attr-defined]
                self.download_button.image = self.download_button_icon  # type: ignore[attr-defined]
                self.animate_button_icon(
                    self.download_button,  # type: ignore[attr-defined]
                    self.download_button_frames,
                    self.download_button_delays,
                )
            else:
                self.download_button.config(image="")  # type: ignore[attr-defined]

    def resource_path(self, relative_path: str) -> str:
        return resolve_resource_path(relative_path)

    def load_custom_font(self, font_path: str, size: int = 16):
        """Load a custom font from file and return a font object."""
        try:
            font_path_abs = self.resource_path(font_path)
            if os.path.exists(font_path_abs):
                custom_font = tkfont.Font(
                    family="Ringbearer",
                    size=size,
                    weight="normal",
                )
                try:
                    custom_font = tkfont.Font(file=font_path_abs, size=size)
                except Exception:
                    try:
                        custom_font = tkfont.Font(family="Ringbearer", size=size)
                    except Exception:
                        custom_font = tkfont.Font(
                            family="Segoe UI",
                            size=size,
                            weight="bold",
                        )
                return custom_font
            print(f"Font file not found: {font_path_abs}")
        except Exception as e:
            print(f"Error loading font: {e}")
        return tkfont.Font(family="Segoe UI", size=size, weight="bold")

    def load_ani_frames(self, ani_path: str, target_size=(32, 32)):
        """Back-compat wrapper (migrated to `ui/ani.py`)."""
        return ui_load_ani_frames(ani_path, target_size=target_size)

    def animate_button_icon(self, button, frames, delays, frame_index: int = 0):
        """Back-compat wrapper (migrated to `ui/effects.py`)."""
        return ui_effects.animate_button_icon(
            self,
            button,
            frames,
            delays,
            frame_index=frame_index,
        )

    def set_custom_cursor(self, widget) -> None:
        """Back-compat wrapper (migrated to `ui/cursors.py`)."""
        return ui_cursors.set_custom_cursor(self, widget)

    def set_ani_cursor(self, widget) -> None:
        """Back-compat wrapper (migrated to `ui/cursors.py`)."""
        return ui_cursors.set_ani_cursor(self, widget)

    def create_background(self) -> None:
        return ui_layout.create_background(self)

    def create_banner(self) -> None:
        return ui_layout.create_banner(self)

    def create_top_buttons(self) -> None:
        return ui_layout.create_top_buttons(self)

    def create_news_section(self) -> None:
        return ui_layout.create_news_section(self)

    def create_bottom_section(self) -> None:
        return ui_layout.create_bottom_section(self)

    def draw_separator_border(self, x, y, width, height, tag: str = "separator") -> None:
        """Back-compat wrapper (migrated to `ui/effects.py`)."""
        return ui_effects.draw_separator_border(self, x, y, width, height, tag=tag)

    def update_canvas_text(self, text_id, text=None, fill=None) -> None:
        """Back-compat wrapper (migrated to `ui/effects.py`)."""
        return ui_effects.update_canvas_text(self, text_id, text=text, fill=fill)

    def style_button(
        self,
        button,
        bg_color: str = "#4a90e2",
        hover_color: str = "#357abd",
        text_color: str = "white",
    ) -> None:
        """Back-compat wrapper (migrated to `ui/effects.py`)."""
        return ui_effects.style_button(
            self,
            button,
            bg_color=bg_color,
            hover_color=hover_color,
            text_color=text_color,
        )

    def _add_text_shadow_to_button(self, button, window_id, font) -> None:
        """Back-compat wrapper (migrated to `ui/effects.py`)."""
        return ui_effects.add_text_shadow_to_button(self, button, window_id, font)

    def add_button_shadow(self, window_id, offset_x: int = 3, offset_y: int = 3):
        """Back-compat wrapper (migrated to `ui/effects.py`)."""
        return ui_effects.add_button_shadow(
            self,
            window_id,
            offset_x=offset_x,
            offset_y=offset_y,
        )

    def add_button_glow(
        self,
        window_id,
        glow_color: str = "#f4d03f",
        glow_size: int = 26,
    ):
        """Back-compat wrapper (migrated to `ui/effects.py`)."""
        return ui_effects.add_button_glow(
            self,
            window_id,
            glow_color=glow_color,
            glow_size=glow_size,
        )

