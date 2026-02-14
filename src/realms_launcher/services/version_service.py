from __future__ import annotations

from dataclasses import dataclass

import requests

from ..constants import MOD_INFO_URL


@dataclass(frozen=True)
class RemoteVersionInfo:
    version: str = "0.0.0"
    launcher_version: str = "0.0.0"
    required_aotr_version: str = "0.0.0"
    current_aotr_version: str = "0.0.0"


def fetch_remote_version_info(
    url: str = MOD_INFO_URL,
    *,
    timeout_s: float = 15.0,
) -> RemoteVersionInfo:
    r = requests.get(url, timeout=timeout_s)
    r.raise_for_status()
    data = r.json() or {}
    return RemoteVersionInfo(
        version=str(data.get("version", "0.0.0")),
        launcher_version=str(data.get("launcher_version", "0.0.0")),
        required_aotr_version=str(data.get("required_aotr_version", "0.0.0")),
        current_aotr_version=str(data.get("current_aotr_version", "0.0.0")),
    )


def is_latest_newer(current_version: str, latest_version: str) -> bool:
    """True if latest_version > current_version (numeric compare)."""
    return _compare_versions(current_version, latest_version) < 0


def is_lower_version(current_version: str, required_version: str) -> bool:
    """True if current_version < required_version (numeric compare)."""
    return _compare_versions(current_version, required_version) < 0


def _compare_versions(a: str, b: str) -> int:
    """Return -1 if a<b, 0 if equal, 1 if a>b."""
    ta = _parse_version_tuple(a)
    tb = _parse_version_tuple(b)
    if ta < tb:
        return -1
    if ta > tb:
        return 1
    return 0


def _parse_version_tuple(v: str) -> tuple[int, ...]:
    parts = []
    for p in (v or "").split("."):
        try:
            parts.append(int(p))
        except ValueError:
            # stop at first non-numeric segment
            break
    # pad for stable compares (common 3-4 segment versions)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


def safe_get_json_value(data: dict, key: str, default: str = "") -> str:
    try:
        v = data.get(key, default)
        return str(v) if v is not None else default
    except Exception:
        return default
