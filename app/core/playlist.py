"""
playlist.py
-----------
Builds and shuffles playable playlists from resolved media sources.

Extensibility note
~~~~~~~~~~~~~~~~~~
``PlaylistBuilder`` accepts any list of path/URI strings, so it works
equally well with local files or future online sources.
"""
from __future__ import annotations

import random
import tempfile
import os
from pathlib import Path


class PlaylistBuilder:
    """
    Builds an mpv-compatible M3U playlist from a list of media paths/URIs.
    """

    def __init__(self, items: list[str]) -> None:
        self._items: list[str] = list(items)

    # ------------------------------------------------------------------
    # Manipulation
    # ------------------------------------------------------------------

    def shuffle(self) -> "PlaylistBuilder":
        """Shuffle in-place and return self for chaining."""
        random.shuffle(self._items)
        return self

    def filter_existing(self) -> "PlaylistBuilder":
        """Remove local paths that no longer exist (skips URIs)."""
        self._items = [
            i for i in self._items
            if i.startswith(("http://", "https://", "ytdl://")) or Path(i).exists()
        ]
        return self

    @property
    def items(self) -> list[str]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def write_m3u(self, path: str) -> str:
        """Write an M3U8 file and return its path."""
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for item in self._items:
                f.write(item + "\n")
        return path

    def write_temp_m3u(self) -> str:
        """Write to a temp file and return its path. Caller must delete."""
        fd, path = tempfile.mkstemp(suffix=".m3u8", prefix="roulette_")
        os.close(fd)
        return self.write_m3u(path)
