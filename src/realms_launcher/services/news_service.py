from __future__ import annotations

import time

import requests

from ..constants import NEWS_URL


def fetch_news_html(url: str = NEWS_URL, *, timeout_s: float = 15.0) -> str:
    """Fetch latest news HTML (cache-busted)."""
    r = requests.get(f"{url}?t={int(time.time())}", timeout=timeout_s)
    if r.status_code == 200:
        return r.text
    return "<p>Failed to fetch news.</p>"

