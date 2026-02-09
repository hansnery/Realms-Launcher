from __future__ import annotations

"""UI effects helpers (Tkinter canvas/button visuals).

These helpers are intentionally UI-only and operate on an `app` context object
that provides `bg_canvas`, `after()`, and any state attributes used by the
original legacy implementations.
"""


def draw_separator_border(app, x, y, width, height, tag: str = "separator") -> None:
    """Draw a separator border around a frame at given position."""
    # Top border
    app.bg_canvas.create_line(
        x - width // 2,
        y - height // 2 - 1,
        x + width // 2,
        y - height // 2 - 1,
        fill="#7f7f7f",
        width=2,
        tags=tag,
    )
    app.bg_canvas.create_rectangle(
        x - width // 2,
        y - height // 2,
        x + width // 2,
        y - height // 2 + 1,
        fill="#5f5f5f",
        outline="",
        tags=tag,
    )

    # Bottom border
    app.bg_canvas.create_rectangle(
        x - width // 2,
        y + height // 2 - 1,
        x + width // 2,
        y + height // 2,
        fill="#5f5f5f",
        outline="",
        tags=tag,
    )
    app.bg_canvas.create_rectangle(
        x - width // 2,
        y + height // 2,
        x + width // 2,
        y + height // 2 + 2,
        fill="#1f1f1f",
        outline="",
        tags=tag,
    )
    app.bg_canvas.create_rectangle(
        x - width // 2,
        y + height // 2 + 2,
        x + width // 2,
        y + height // 2 + 4,
        fill="#0f0f0f",
        outline="",
        tags=tag,
    )

    # Left border
    app.bg_canvas.create_line(
        x - width // 2 - 1,
        y - height // 2,
        x - width // 2 - 1,
        y + height // 2,
        fill="#5f5f5f",
        width=2,
        tags=tag,
    )

    # Right border
    app.bg_canvas.create_line(
        x + width // 2 + 1,
        y - height // 2,
        x + width // 2 + 1,
        y + height // 2,
        fill="#5f5f5f",
        width=2,
        tags=tag,
    )


def update_canvas_text(app, text_id, text: str | None = None, fill: str | None = None) -> None:
    """Update a canvas text item's text and/or color."""
    if text is not None:
        app.bg_canvas.itemconfig(text_id, text=text)
    if fill is not None:
        app.bg_canvas.itemconfig(text_id, fill=fill)


def style_button(
    _app,
    button,
    bg_color: str = "#4a90e2",
    hover_color: str = "#357abd",
    text_color: str = "white",
) -> None:
    """Style a button with modern colors, border, shadow, and hover effects."""
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
        activeforeground=text_color,
    )

    def on_enter(_e):
        button.config(bg=hover_color, relief="raised")

    def on_leave(_e):
        button.config(bg=bg_color, relief="raised")

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)


def add_text_shadow_to_button(app, button, window_id, font) -> None:
    """Add a text shadow effect to button text using a canvas overlay."""

    def update_text_shadow():
        # Clear previous shadow text
        for text_id in app.download_button_text_shadow_ids:
            try:
                app.bg_canvas.delete(text_id)
            except Exception:
                pass
        app.download_button_text_shadow_ids = []

        try:
            bbox = app.bg_canvas.bbox(window_id)
            if not bbox:
                # Retry after a short delay if bbox not available
                app.after(100, update_text_shadow)
                return

            x1, y1, x2, y2 = bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            button_text = button.cget("text")
            if not button_text:
                return

            shadow_offset_x = 2
            shadow_offset_y = 2

            try:
                font_family = font.cget("family")
                font_size = font.cget("size")
                font_weight = font.cget("weight")
                canvas_font = (font_family, font_size, font_weight)
            except Exception:
                canvas_font = ("Segoe UI", 16, "bold")

            shadow_id = app.bg_canvas.create_text(
                center_x + shadow_offset_x,
                center_y + shadow_offset_y,
                text=button_text,
                font=canvas_font,
                fill="#000000",
                anchor="center",
                state="normal",
            )
            app.download_button_text_shadow_ids.append(shadow_id)
            app.bg_canvas.tag_raise(shadow_id, window_id)

            main_text_id = app.bg_canvas.create_text(
                center_x,
                center_y,
                text=button_text,
                font=canvas_font,
                fill="white",
                anchor="center",
                state="normal",
            )
            app.download_button_text_shadow_ids.append(main_text_id)
            app.bg_canvas.tag_raise(main_text_id, shadow_id)
            app.bg_canvas.tag_raise(main_text_id, window_id)
            app.bg_canvas.tag_raise(main_text_id)

            current_bg = button.cget("bg")
            button.config(fg=current_bg)

            # Bind to hover events to keep text hidden
            if not hasattr(button, "_text_shadow_hover_bound"):

                def on_enter_hover(_e):
                    hover_bg = button.cget("activebackground")
                    button.config(fg=hover_bg)
                    for tid in app.download_button_text_shadow_ids:
                        try:
                            app.bg_canvas.itemconfig(tid, state="normal")
                            app.bg_canvas.tag_raise(tid)
                        except Exception:
                            pass
                    app.after(10, update_text_shadow)

                def on_leave_hover(_e):
                    normal_bg = button.cget("bg")
                    button.config(fg=normal_bg)
                    for tid in app.download_button_text_shadow_ids:
                        try:
                            app.bg_canvas.itemconfig(tid, state="normal")
                            app.bg_canvas.tag_raise(tid)
                        except Exception:
                            pass
                    app.after(10, update_text_shadow)

                button.bind("<Enter>", on_enter_hover, add="+")
                button.bind("<Leave>", on_leave_hover, add="+")
                button._text_shadow_hover_bound = True

            def periodic_check():
                try:
                    current_bg = button.cget("bg")
                    button.config(fg=current_bg)
                    for tid in app.download_button_text_shadow_ids:
                        try:
                            app.bg_canvas.itemconfig(tid, state="normal")
                            app.bg_canvas.tag_raise(tid)
                        except Exception:
                            pass
                except Exception:
                    pass
                app.after(200, periodic_check)

            app.after(200, periodic_check)
        except Exception as e:
            print(f"Error adding text shadow: {e}")
            import traceback

            traceback.print_exc()

    app.after(50, update_text_shadow)
    app.after(150, update_text_shadow)
    app.after(300, update_text_shadow)

    # Store update function for manual calls
    app._download_button_text_shadow_update = update_text_shadow


def add_button_shadow(app, window_id, offset_x: int = 3, offset_y: int = 3):
    """Add a shadow effect behind a canvas window item."""
    try:
        coords = app.bg_canvas.coords(window_id)
        if coords:
            bbox = app.bg_canvas.bbox(window_id)
            if bbox:
                x1, y1, x2, y2 = bbox
                shadow_id = app.bg_canvas.create_rectangle(
                    x1 + offset_x,
                    y1 + offset_y,
                    x2 + offset_x,
                    y2 + offset_y,
                    fill="#000000",
                    outline="",
                    stipple="gray12",
                )
                app.bg_canvas.tag_lower(shadow_id, window_id)
                try:
                    app.button_shadows[window_id] = shadow_id
                except Exception:
                    pass
                return shadow_id
    except Exception:
        pass
    return None


def add_button_glow(app, window_id, glow_color: str = "#f4d03f", glow_size: int = 26) -> list[int]:
    """Add an outer glow around a canvas window item."""

    def get_glow_color(distance_ratio, base_color):
        # Blend base color towards white as it moves outward
        try:
            base = base_color.lstrip("#")
            r = int(base[0:2], 16)
            g = int(base[2:4], 16)
            b = int(base[4:6], 16)
            t = min(1.0, max(0.0, distance_ratio))  # 0..1
            rr = int(r + (255 - r) * t)
            gg = int(g + (255 - g) * t)
            bb = int(b + (255 - b) * t)
            return f"#{rr:02x}{gg:02x}{bb:02x}"
        except Exception:
            return base_color

    try:
        bbox = app.bg_canvas.bbox(window_id)
        if bbox:
            x1, y1, x2, y2 = bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = x2 - x1
            height = y2 - y1

            glow_ids: list[int] = []
            num_layers = 24

            for i in range(num_layers):
                layer_size = (glow_size * i) / num_layers
                distance_ratio = i / num_layers
                if distance_ratio < 0.15:
                    stipple_pattern = "gray75"
                elif distance_ratio < 0.4:
                    stipple_pattern = "gray50"
                elif distance_ratio < 0.7:
                    stipple_pattern = "gray25"
                else:
                    stipple_pattern = "gray12"
                layer_color = get_glow_color(distance_ratio, glow_color)

                glow_id = app.bg_canvas.create_oval(
                    center_x - width / 2 - layer_size,
                    center_y - height / 2 - layer_size,
                    center_x + width / 2 + layer_size,
                    center_y + height / 2 + layer_size,
                    fill=layer_color,
                    outline="",
                    stipple=stipple_pattern,
                )
                glow_ids.append(glow_id)
                app.bg_canvas.tag_lower(glow_id, window_id)

            for glow_id in glow_ids:
                app.bg_canvas.itemconfig(glow_id, state="hidden")

            return glow_ids

        print(f"Warning: Could not get bounding box for window_id {window_id}")
        return []
    except Exception as e:
        print(f"Error creating glow: {e}")
        import traceback

        traceback.print_exc()
    return []


def animate_button_icon(app, button, frames, delays, frame_index: int = 0) -> None:
    """Animate a button icon by cycling through frames."""
    if not frames or frame_index >= len(frames):
        return

    button.config(image=frames[frame_index])
    button.image = frames[frame_index]

    delay = delays[frame_index] if delays and frame_index < len(delays) else 100
    next_index = (frame_index + 1) % len(frames)
    app._download_button_animation_id = app.after(
        delay,
        lambda: animate_button_icon(app, button, frames, delays, next_index),
    )

