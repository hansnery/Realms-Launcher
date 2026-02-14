from __future__ import annotations


class ButtonVisibilityMixin:
    """Show/hide helpers and positioning logic for canvas window items."""

    def show_download_button(self) -> None:
        self.bg_canvas.itemconfig(self.download_button_window, state="normal")  # type: ignore[attr-defined]
        try:
            shadow_id = self.button_shadows.get(self.download_button_window)  # type: ignore[attr-defined]
            if shadow_id:
                self.bg_canvas.itemconfig(shadow_id, state="normal")  # type: ignore[attr-defined]
        except Exception:
            pass

    def hide_download_button(self) -> None:
        self.bg_canvas.itemconfig(self.download_button_window, state="hidden")  # type: ignore[attr-defined]
        try:
            shadow_id = self.button_shadows.get(self.download_button_window)  # type: ignore[attr-defined]
            if shadow_id:
                self.bg_canvas.itemconfig(shadow_id, state="hidden")  # type: ignore[attr-defined]
        except Exception:
            pass

    def show_play_button(self) -> None:
        if not hasattr(self, "play_button_window"):
            self.play_button_window = self.bg_canvas.create_window(  # type: ignore[attr-defined]
                400,
                550,
                window=self.play_button,  # type: ignore[attr-defined]
                anchor="center",
            )
            self.after(10, lambda: self.add_button_shadow(self.play_button_window))  # type: ignore[attr-defined]
        self.bg_canvas.itemconfig(self.play_button_window, state="normal")  # type: ignore[attr-defined]
        try:
            shadow_id = self.button_shadows.get(self.play_button_window)  # type: ignore[attr-defined]
            if shadow_id:
                self.bg_canvas.itemconfig(shadow_id, state="normal")  # type: ignore[attr-defined]
        except Exception:
            pass

    def hide_play_button(self) -> None:
        if hasattr(self, "play_button_window"):
            self.bg_canvas.itemconfig(self.play_button_window, state="hidden")  # type: ignore[attr-defined]
            if hasattr(self, "play_button_glow_ids"):
                for glow_id in self.play_button_glow_ids:  # type: ignore[attr-defined]
                    self.bg_canvas.itemconfig(glow_id, state="hidden")  # type: ignore[attr-defined]
            try:
                shadow_id = self.button_shadows.get(self.play_button_window)  # type: ignore[attr-defined]
                if shadow_id:
                    self.bg_canvas.itemconfig(shadow_id, state="hidden")  # type: ignore[attr-defined]
            except Exception:
                pass

    def _setup_play_button_glow(self) -> None:
        if hasattr(self, "play_button_window"):
            self.play_button_glow_ids = self.add_button_glow(  # type: ignore[attr-defined]
                self.play_button_window,
                glow_color="#f4d03f",
                glow_size=18,
            )

            def on_enter(_e):
                if getattr(self, "play_button_glow_ids", None):
                    for glow_id in self.play_button_glow_ids:  # type: ignore[attr-defined]
                        self.bg_canvas.itemconfig(glow_id, state="normal")  # type: ignore[attr-defined]
                    self.bg_canvas.update_idletasks()  # type: ignore[attr-defined]

            def on_leave(_e):
                if getattr(self, "play_button_glow_ids", None):
                    for glow_id in self.play_button_glow_ids:  # type: ignore[attr-defined]
                        self.bg_canvas.itemconfig(glow_id, state="hidden")  # type: ignore[attr-defined]
                    self.bg_canvas.update_idletasks()  # type: ignore[attr-defined]

            self.play_button.bind("<Enter>", on_enter)  # type: ignore[attr-defined]
            self.play_button.bind("<Leave>", on_leave)  # type: ignore[attr-defined]

    def show_folder_button(self) -> None:
        if hasattr(self, "folder_button_window"):
            self.bg_canvas.itemconfig(self.folder_button_window, state="normal")  # type: ignore[attr-defined]

    def hide_folder_button(self) -> None:
        if hasattr(self, "folder_button_window"):
            self.bg_canvas.itemconfig(self.folder_button_window, state="hidden")  # type: ignore[attr-defined]

    def _update_folder_button_position(self) -> None:
        if not hasattr(self, "folder_button_window"):
            return

        uninstall_visible = False

        if hasattr(self, "uninstall_button_window"):
            try:
                state = self.bg_canvas.itemcget(self.uninstall_button_window, "state")  # type: ignore[attr-defined]
                uninstall_visible = state == "normal"
            except Exception:
                pass

        new_x = 400 if not uninstall_visible else 100

        try:
            coords = self.bg_canvas.coords(self.folder_button_window)  # type: ignore[attr-defined]
            if coords:
                current_y = coords[1]
                self.bg_canvas.coords(self.folder_button_window, new_x, current_y)  # type: ignore[attr-defined]
        except Exception:
            pass

    def show_uninstall_button(self) -> None:
        if hasattr(self, "uninstall_button_window"):
            self.bg_canvas.itemconfig(self.uninstall_button_window, state="normal")  # type: ignore[attr-defined]
            self._update_folder_button_position()

    def hide_uninstall_button(self) -> None:
        if hasattr(self, "uninstall_button_window"):
            self.bg_canvas.itemconfig(self.uninstall_button_window, state="hidden")  # type: ignore[attr-defined]
            self._update_folder_button_position()


