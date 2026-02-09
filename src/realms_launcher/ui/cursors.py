from __future__ import annotations

import os


def set_custom_cursor(app, widget) -> None:
    """Set the custom cursor (.cur) on a widget (best-effort)."""
    cursor_path = app.resource_path("SCCpointer.cur")
    if not os.path.exists(cursor_path):
        return

    abs_cursor_path = os.path.abspath(cursor_path)
    tk_cursor_path = abs_cursor_path.replace("\\", "/")

    # Method 1: @ + forward slashes
    try:
        widget.config(cursor=f"@{tk_cursor_path}")
        return
    except Exception:
        pass

    # Method 2: @ + backslashes
    try:
        widget.config(cursor=f"@{abs_cursor_path}")
        return
    except Exception:
        pass

    # Method 3: no @
    try:
        widget.config(cursor=tk_cursor_path)
        return
    except Exception:
        pass

    # Method 4: filename only
    try:
        cursor_filename = os.path.basename(cursor_path)
        widget.config(cursor=f"@{cursor_filename}")
        return
    except Exception:
        pass

    print(f"Warning: Could not set custom cursor from {cursor_path}")


def set_ani_cursor(app, widget) -> None:
    """Set the animated cursor (.ani) on a widget (best-effort)."""
    ani_path = app.resource_path("OneRing.ani")
    if not os.path.exists(ani_path):
        return

    abs_ani_path = os.path.abspath(ani_path)
    tk_ani_path = abs_ani_path.replace("\\", "/")

    # Method 1: @ + forward slashes
    try:
        widget.config(cursor=f"@{tk_ani_path}")
        return
    except Exception:
        pass

    # Method 2: @ + backslashes
    try:
        widget.config(cursor=f"@{abs_ani_path}")
        return
    except Exception:
        pass

    # Method 3: no @
    try:
        widget.config(cursor=tk_ani_path)
        return
    except Exception:
        pass

    # Method 4: filename only
    try:
        ani_filename = os.path.basename(ani_path)
        widget.config(cursor=f"@{ani_filename}")
        return
    except Exception:
        pass

    print(f"Warning: Could not set animated cursor from {ani_path}")

