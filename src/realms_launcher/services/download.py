from __future__ import annotations

from collections.abc import Callable

import requests


ProgressCallback = Callable[[int, int], None]  # (bytes_received, total_bytes)


def download_to_file(
    url: str,
    dest_path: str,
    *,
    chunk_size: int = 1 << 14,
    timeout_s: float = 30.0,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Stream-download a URL to dest_path with optional progress callback."""
    r = requests.get(url, stream=True, timeout=timeout_s)
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0) or 0)
    received = 0

    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue
            f.write(chunk)
            received += len(chunk)
            if on_progress is not None:
                on_progress(received, total)

