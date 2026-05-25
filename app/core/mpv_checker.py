"""
mpv_checker.py
--------------
Detects whether mpv is available on the system and, if not, attempts to
install it via Homebrew (the macOS industry standard).

Extensibility note
~~~~~~~~~~~~~~~~~~
To support Linux or Windows, subclass ``MpvInstaller`` and register it in
``_get_installer()``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path

# Common install locations that macOS .app bundles do not include in PATH.
_EXTRA_DIRS: list[str] = [
    "/usr/local/bin",       # Homebrew on Intel
    "/opt/homebrew/bin",    # Homebrew on Apple Silicon
    "/opt/local/bin",       # MacPorts
]


def _which_extended(name: str) -> str | None:
    """Like shutil.which but also probes _EXTRA_DIRS as fallback."""
    found = shutil.which(name)
    if found:
        return found
    for directory in _EXTRA_DIRS:
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_mpv_available() -> bool:
    """Return True if mpv is on the PATH (or a known install location) and executable."""
    return _which_extended("mpv") is not None


def ensure_mpv(progress_callback=None) -> bool:
    """
    Check for mpv; install if missing.

    Parameters
    ----------
    progress_callback:
        Optional callable(str) for status messages (used by the UI).

    Returns
    -------
    bool
        True  – mpv is ready to use.
        False – installation failed or was not possible.
    """
    if is_mpv_available():
        return True

    installer = _get_installer()
    if installer is None:
        _log(progress_callback, "No automatic installer available for this platform.")
        return False

    return installer.install(progress_callback)


def get_mpv_path() -> str | None:
    """Return the absolute path to the mpv binary, or None."""
    return _which_extended("mpv")


# ---------------------------------------------------------------------------
# Internal installer abstraction
# ---------------------------------------------------------------------------

class MpvInstaller(ABC):
    @abstractmethod
    def install(self, progress_callback=None) -> bool: ...


class _HomebrewInstaller(MpvInstaller):
    """Install mpv via Homebrew on macOS."""

    def install(self, progress_callback=None) -> bool:
        brew = _which_extended("brew")
        if brew is None:
            _log(progress_callback, "Homebrew not found. Installing Homebrew first…")
            brew = self._install_homebrew(progress_callback)
            if brew is None:
                _log(progress_callback, "Homebrew installation failed. Please install mpv manually.")
                return False

        _log(progress_callback, "Installing mpv via Homebrew…")
        result = subprocess.run(
            [brew, "install", "mpv"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            _log(progress_callback, "mpv installed successfully.")
            return True

        _log(progress_callback, f"Homebrew install failed:\n{result.stderr.strip()}")
        return False

    @staticmethod
    def _install_homebrew(progress_callback=None) -> str | None:
        """
        Run the official Homebrew install script non-interactively.
        Returns the brew binary path on success, None on failure.
        """
        install_cmd = (
            '/bin/bash -c "$(curl -fsSL '
            'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        )
        result = subprocess.run(install_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return None
        return _which_extended("brew")


class _WingetInstaller(MpvInstaller):
    """Install mpv via winget on Windows (Windows 10 1709+ / Windows 11)."""

    def install(self, progress_callback=None) -> bool:
        winget = shutil.which("winget")
        if winget is None:
            _log(
                progress_callback,
                "winget not found. Please install mpv manually from https://mpv.io/installation/",
            )
            return False

        _log(progress_callback, "Installing mpv via winget…")
        result = subprocess.run(
            [winget, "install", "--id", "mpv.mpv", "-e", "--silent"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            _log(progress_callback, "mpv installed successfully.")
            return True

        # winget may return non-zero if already installed; check PATH again
        if shutil.which("mpv") is not None:
            _log(progress_callback, "mpv is already available.")
            return True

        _log(progress_callback, f"winget install failed:\n{result.stderr.strip()}")
        return False


def _get_installer() -> MpvInstaller | None:
    if sys.platform == "darwin":
        return _HomebrewInstaller()
    if sys.platform == "win32":
        return _WingetInstaller()
    # Future: add _AptInstaller for Linux, etc.
    return None


def _log(callback, message: str) -> None:
    if callback:
        callback(message)
    else:
        print(message)
