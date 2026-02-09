from __future__ import annotations

import struct
from io import BytesIO

from PIL import Image, ImageTk


def load_ani_frames(ani_path: str, *, target_size: tuple[int, int] = (32, 32)):
    """Extract frames from Windows .ani animated cursor file.

    Returns (frames, delays_ms) or (None, None) on failure.
    """
    try:
        frames = []
        frame_delays: list[int] = []

        with open(ani_path, "rb") as f:
            riff = f.read(4)
            if riff != b"RIFF":
                raise ValueError("Not a valid RIFF file")

            file_size = struct.unpack("<I", f.read(4))[0]
            ani_type = f.read(4)
            if ani_type != b"ACON":
                raise ValueError("Not a valid ANI file")

            end_pos = file_size + 8
            while f.tell() < end_pos:
                chunk_id = f.read(4)
                if len(chunk_id) < 4:
                    break

                chunk_size = struct.unpack("<I", f.read(4))[0]
                chunk_start = f.tell()

                if chunk_id == b"LIST":
                    list_type = f.read(4)
                    if list_type == b"fram":
                        list_end = chunk_start + chunk_size - 4
                        while f.tell() < list_end:
                            sub_chunk_id = f.read(4)
                            if len(sub_chunk_id) < 4:
                                break
                            sub_chunk_size = struct.unpack("<I", f.read(4))[0]

                            if sub_chunk_id == b"icon":
                                icon_data = f.read(sub_chunk_size)
                                try:
                                    icon_image = Image.open(BytesIO(icon_data))

                                    if icon_image.mode in (
                                        "P",
                                        "RGB",
                                    ) or icon_image.mode not in ("RGBA", "LA"):
                                        icon_image = icon_image.convert("RGBA")

                                    # Make pure black pixels transparent (best-effort)
                                    if icon_image.mode == "RGBA":
                                        data = icon_image.getdata()
                                        new_data = []
                                        for item in data:
                                            r, g, b, a = item
                                            if (
                                                r == 0
                                                and g == 0
                                                and b == 0
                                                and a > 0
                                            ):
                                                new_data.append((0, 0, 0, 0))
                                            else:
                                                new_data.append(item)
                                        icon_image.putdata(new_data)

                                    # Resize while preserving aspect ratio, then center on canvas
                                    tw, th = target_size
                                    w, h = icon_image.size
                                    scale = (
                                        min(tw / float(w), th / float(h))
                                        if w and h
                                        else 1.0
                                    )
                                    new_w = max(1, int(round(w * scale)))
                                    new_h = max(1, int(round(h * scale)))
                                    resized = icon_image.resize(
                                        (new_w, new_h),
                                        Image.Resampling.LANCZOS,
                                    )
                                    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
                                    offset_x = (tw - new_w) // 2
                                    offset_y = (th - new_h) // 2
                                    canvas.paste(resized, (offset_x, offset_y), resized)
                                    icon_image = canvas

                                    frames.append(
                                        ImageTk.PhotoImage(icon_image)
                                    )
                                except Exception:
                                    pass
                            else:
                                f.seek(sub_chunk_size, 1)

                elif chunk_id == b"rate":
                    rate_data = f.read(min(chunk_size, 256))
                    for i in range(0, len(rate_data) - 3, 4):
                        delay_jiffies = struct.unpack(
                            "<I",
                            rate_data[i:i + 4],
                        )[0]
                        delay_ms = (
                            int((delay_jiffies / 60.0) * 1000)
                            if delay_jiffies > 0
                            else 100
                        )
                        frame_delays.append(max(50, min(delay_ms, 1000)))
                else:
                    f.seek(chunk_start + chunk_size)

        if not frames:
            return None, None

        if not frame_delays or len(frame_delays) != len(frames):
            frame_delays = [100] * len(frames)

        return frames, frame_delays
    except Exception:
        return None, None
