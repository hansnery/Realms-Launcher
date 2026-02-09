from __future__ import annotations


class LauncherError(Exception):
    """Base error for domain failures that should be shown to the user."""


class DownloadError(LauncherError):
    pass


class InstallError(LauncherError):
    pass


class UpdateError(LauncherError):
    pass

