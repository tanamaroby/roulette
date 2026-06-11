"""
mpv_ipc.py
----------
Minimal mpv JSON IPC client (Unix socket — macOS / Linux).

On Windows, mpv uses named pipes which require platform-specific code;
all public methods are no-ops on that platform.

Protocol reference: https://mpv.io/manual/stable/#json-ipc
"""
from __future__ import annotations

import json
import socket
import sys
import time
from typing import Any


class MpvIpc:
    """
    Connects to the mpv IPC socket and sends JSON commands.

    Call ``connect()`` after launching mpv (it retries until the socket
    appears).  Use ``show_osd()`` to send on-screen messages back to mpv.
    Call ``close()`` when playback ends.
    """

    def __init__(self, socket_path: str) -> None:
        self._path = socket_path
        self._sock: socket.socket | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self, retries: int = 14, delay: float = 0.25) -> bool:
        """
        Try to connect, retrying up to *retries* times with *delay* seconds
        between attempts (mpv creates the socket after it has started).

        Returns True on success.  Always returns False on Windows.
        """
        if sys.platform == "win32":
            return False
        for _ in range(retries):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect(self._path)
                self._sock = sock
                return True
            except OSError:
                time.sleep(delay)
        return False

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def send_command(self, *args: Any) -> dict | None:
        """
        Send a JSON IPC command and return the parsed response dict,
        or None if the socket is not connected or an error occurs.
        """
        if self._sock is None:
            return None
        payload = json.dumps({"command": list(args)}) + "\n"
        try:
            self._sock.sendall(payload.encode())
            raw = b""
            while b"\n" not in raw:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                raw += chunk
            return json.loads(raw.split(b"\n")[0])
        except (OSError, json.JSONDecodeError):
            return None

    def show_osd(self, text: str, duration_ms: int = 3000) -> None:
        """Display *text* on the mpv on-screen display for *duration_ms* ms."""
        self.send_command("show-text", text, duration_ms)
