"""
player.py
---------
Constructs and launches mpv with a configurable set of flags.

Design
~~~~~~
``MpvFlags`` is a plain dataclass that maps cleanly to mpv CLI options.
``MpvPlayer`` turns those flags into a subprocess call.

Extensibility note
~~~~~~~~~~~~~~~~~~
Add new flag fields to ``MpvFlags`` and handle them in
``MpvPlayer._build_args()``.  No other module needs to change.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.core.mpv_checker import get_mpv_path


# ---------------------------------------------------------------------------
# Flags dataclass
# ---------------------------------------------------------------------------

@dataclass
class MpvFlags:
    """
    All toggleable mpv options surfaced by the UI.

    Defaults reflect the project requirement:
    fullscreen=True, shuffle=True, loop_playlist="inf" (single infinite loop).
    """
    fullscreen: bool = True
    shuffle: bool = True
    loop_playlist: str = "inf"        # "inf" | "no" | "force" | int str
    loop_file: str = "inf"            # "inf" | "no" | int str

    # Playback
    volume: int = 100                 # 0–130
    speed: float = 1.0
    mute: bool = False

    # Video
    hwdec: str = "auto"              # hardware decoding mode
    sub_auto: str = "fuzzy"          # subtitle auto-load
    audio_delay: float = 0.0         # seconds
    video_zoom: float = 0.0          # mpv --video-zoom

    # Window
    ontop: bool = False
    no_border: bool = False
    autofit: str = ""                 # e.g. "50%" — empty = default

    # Extra raw flags (list of "--flag=value" or "--flag" strings)
    extra_flags: list[str] = field(default_factory=list)

    # Download support (set programmatically — not exposed in the UI)
    ipc_socket_path: str = ""              # --input-ipc-server
    script_paths: list[str] = field(default_factory=list)  # --script=


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

class MpvPlayer:
    """
    Launches mpv as a subprocess with the given playlist and flags.
    """

    def __init__(
        self,
        flags: MpvFlags | None = None,
        on_exit: Callable[[int], None] | None = None,
    ) -> None:
        self.flags = flags or MpvFlags()
        self.on_exit = on_exit
        self._process: subprocess.Popen | None = None
        self._temp_playlist: str | None = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def play(self, playlist_path: str) -> None:
        """Launch mpv with the given M3U playlist file."""
        mpv = get_mpv_path()
        if mpv is None:
            raise RuntimeError("mpv is not installed or not on PATH.")

        args = self._build_args(mpv, playlist_path)
        self._process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if self.on_exit:
            # Poll in a background thread so as not to block the UI.
            import threading
            threading.Thread(target=self._wait, daemon=True).start()

    def stop(self) -> None:
        """Terminate the running mpv process, if any."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
        self._cleanup_temp()

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_args(self, mpv: str, playlist_path: str) -> list[str]:
        f = self.flags
        args: list[str] = [mpv]

        if f.fullscreen:
            args.append("--fullscreen")

        # playlist flags
        args.append(f"--loop-playlist={f.loop_playlist}")
        args.append(f"--loop-file={f.loop_file}")

        # Note: mpv has built-in shuffle via --shuffle
        if f.shuffle:
            args.append("--shuffle")

        args.append(f"--volume={f.volume}")
        args.append(f"--speed={f.speed}")

        if f.mute:
            args.append("--mute=yes")

        if f.hwdec:
            args.append(f"--hwdec={f.hwdec}")

        if f.sub_auto:
            args.append(f"--sub-auto={f.sub_auto}")

        if f.audio_delay != 0.0:
            args.append(f"--audio-delay={f.audio_delay}")

        if f.video_zoom != 0.0:
            args.append(f"--video-zoom={f.video_zoom}")

        if f.ontop:
            args.append("--ontop")

        if f.no_border:
            args.append("--no-border")

        if f.autofit:
            args.append(f"--autofit={f.autofit}")

        # Raw extra flags (user-defined)
        args.extend(f.extra_flags)

        # IPC socket and Lua scripts (download support)
        if f.ipc_socket_path:
            args.append(f"--input-ipc-server={f.ipc_socket_path}")
        for sp in f.script_paths:
            args.append(f"--script={sp}")

        # Playlist file must come last
        args.append(f"--playlist={playlist_path}")

        return args

    def _wait(self) -> None:
        if self._process:
            code = self._process.wait()
            self._cleanup_temp()
            if self.on_exit:
                self.on_exit(code)

    def _cleanup_temp(self) -> None:
        if self._temp_playlist and Path(self._temp_playlist).exists():
            try:
                os.remove(self._temp_playlist)
            except OSError:
                pass
        self._temp_playlist = None
