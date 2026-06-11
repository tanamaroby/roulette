"""
folder_manager.py
-----------------
Persists the user's saved media folders and resolves them to lists of
media file paths.

Storage
~~~~~~~
Saved folders are written to ``~/.config/roulette/folders.json``.

Extensibility note
~~~~~~~~~~~~~~~~~~
``MediaResolver`` is the single point for deciding which files count as
"media".  Swap or subclass it to add online-source resolvers in the future.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# Supported extensions
# ---------------------------------------------------------------------------

VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mkv", ".mp4", ".avi", ".mov", ".webm", ".flv", ".m4v", ".wmv", ".ts",
     ".m2ts", ".mpg", ".mpeg", ".ogv", ".3gp", ".divx", ".rm", ".rmvb"}
)

AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp3", ".flac", ".aac", ".ogg", ".wav", ".m4a", ".opus", ".wma"}
)

ALL_MEDIA_EXTENSIONS: frozenset[str] = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# ---------------------------------------------------------------------------
# Config path
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path.home() / ".config" / "roulette"
_FOLDERS_FILE = _CONFIG_DIR / "folders.json"


# ---------------------------------------------------------------------------
# Folder manager
# ---------------------------------------------------------------------------

class FolderManager:
    """
    Manages a persistent list of media source folders.
    """

    def __init__(self) -> None:
        self._folders: list[dict[str, object]] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if _FOLDERS_FILE.exists():
            try:
                data = json.loads(_FOLDERS_FILE.read_text(encoding="utf-8"))
                self._folders = self._normalize_folders(data.get("folders", []))
            except (json.JSONDecodeError, OSError):
                self._folders = []

    def _normalize_folders(self, folders: object) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        if not isinstance(folders, list):
            return normalized

        for entry in folders:
            if isinstance(entry, str):
                path = str(Path(entry).resolve())
                include = True
            elif isinstance(entry, dict):
                raw_path = entry.get("path")
                if not isinstance(raw_path, str):
                    continue
                path = str(Path(raw_path).resolve())
                include = bool(entry.get("include", True))
            else:
                continue

            if os.path.isdir(path):
                normalized.append({"path": path, "include": include})

        return normalized

    def save(self) -> None:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _FOLDERS_FILE.write_text(
            json.dumps({"folders": self._folders}, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @property
    def folders(self) -> list[str]:
        return [entry["path"] for entry in self._folders]

    @property
    def enabled_folders(self) -> list[str]:
        return [entry["path"] for entry in self._folders if entry.get("include", True)]

    def is_included(self, path: str) -> bool:
        path = str(Path(path).resolve())
        for entry in self._folders:
            if entry["path"] == path:
                return bool(entry.get("include", True))
        return True

    def add_folder(self, path: str, include: bool = True) -> bool:
        """Add a folder. Returns False if already present or not a directory."""
        path = str(Path(path).resolve())
        if not os.path.isdir(path):
            return False
        if path not in self.folders:
            self._folders.append({"path": path, "include": include})
            self.save()
        return True

    def remove_folder(self, path: str) -> None:
        path = str(Path(path).resolve())
        self._folders = [entry for entry in self._folders if entry["path"] != path]
        self.save()

    def set_folder_included(self, path: str, include: bool) -> None:
        path = str(Path(path).resolve())
        for entry in self._folders:
            if entry["path"] == path:
                entry["include"] = include
                self.save()
                return
        self.save()

    def clear(self) -> None:
        self._folders.clear()
        self.save()

    # ------------------------------------------------------------------
    # Media resolution
    # ------------------------------------------------------------------

    def resolve_all_media(
        self,
        extensions: frozenset[str] = ALL_MEDIA_EXTENSIONS,
        recursive: bool = True,
        include_disabled: bool = False,
    ) -> list[str]:
        """
        Return a flat list of all media files found across saved folders.
        """
        resolver = LocalMediaResolver(extensions=extensions, recursive=recursive)
        files: list[str] = []
        folders = self._folders if include_disabled else [entry for entry in self._folders if entry.get("include", True)]
        for folder in folders:
            files.extend(resolver.resolve(folder["path"]))
        return files


# ---------------------------------------------------------------------------
# Media resolver abstraction (extensible)
# ---------------------------------------------------------------------------

class MediaResolver:
    """
    Base class for resolving a source into a list of playable paths/URIs.

    Subclass this to support new sources (e.g. YouTube playlists, network
    shares, streaming services).
    """

    def resolve(self, source: str) -> list[str]:
        raise NotImplementedError


class LocalMediaResolver(MediaResolver):
    """Resolves a local directory to a list of media file paths."""

    def __init__(
        self,
        extensions: frozenset[str] = ALL_MEDIA_EXTENSIONS,
        recursive: bool = True,
    ) -> None:
        self.extensions = extensions
        self.recursive = recursive

    def resolve(self, source: str) -> list[str]:
        root = Path(source)
        if not root.is_dir():
            return []
        iterator: Iterator[Path] = root.rglob("*") if self.recursive else root.iterdir()
        return sorted(
            str(p) for p in iterator
            if p.is_file() and p.suffix.lower() in self.extensions
        )
