"""
downloader.py
-------------
Downloads URLs to a destination folder in background threads, tracking every
item in a live queue so the UI can display progress.

Existing files are silently replaced (user intent: save this specific video).
"""
from __future__ import annotations

import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable


class DownloadState(Enum):
    QUEUED = auto()
    DOWNLOADING = auto()
    DONE = auto()
    FAILED = auto()


@dataclass
class DownloadItem:
    filename: str
    url: str
    state: DownloadState = DownloadState.QUEUED
    dest: str = ""        # populated on DONE
    error: str = ""       # populated on FAILED


class Downloader:
    """
    Downloads URLs to *dest_folder*, one background thread per item.

    A live ``queue`` list (``list[DownloadItem]``) is kept in insertion order.
    Every state transition calls ``on_queue_changed(queue)`` on the calling
    thread (i.e. the background download thread — callers must marshal to the
    UI thread themselves).

    Parameters
    ----------
    dest_folder:
        Target directory.  Created (including parents) if absent.
    on_queue_changed:
        Optional callback fired after every state change, receiving a
        snapshot of the current queue.
    """

    def __init__(
        self,
        dest_folder: str | Path,
        on_queue_changed: Callable[[list[DownloadItem]], None] | None = None,
    ) -> None:
        self._folder = Path(dest_folder)
        self._on_queue_changed = on_queue_changed
        self._lock = threading.Lock()
        self.queue: list[DownloadItem] = []

    def start(
        self,
        url: str,
        on_done: Callable[[Path], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Enqueue *url* and kick off a background download immediately."""
        item = DownloadItem(filename=_filename_from_url(url), url=url)
        with self._lock:
            self.queue.append(item)
        self._notify()
        threading.Thread(
            target=self._run,
            args=(item, on_done, on_error),
            daemon=True,
        ).start()

    def snapshot(self) -> list[DownloadItem]:
        """Return a thread-safe copy of the current queue."""
        with self._lock:
            return list(self.queue)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(
        self,
        item: DownloadItem,
        on_done: Callable[[Path], None] | None,
        on_error: Callable[[str], None] | None,
    ) -> None:
        try:
            self._folder.mkdir(parents=True, exist_ok=True)
            dest = self._folder / item.filename
            req = urllib.request.Request(
                item.url, headers={"User-Agent": "Roulette-MediaShuffler/1.0"}
            )
            with self._lock:
                item.state = DownloadState.DOWNLOADING
            self._notify()
            with urllib.request.urlopen(req) as resp, open(dest, "wb") as fh:
                while chunk := resp.read(65536):
                    fh.write(chunk)
            with self._lock:
                item.state = DownloadState.DONE
                item.dest = str(dest)
            self._notify()
            if on_done:
                on_done(dest)
        except Exception as exc:
            with self._lock:
                item.state = DownloadState.FAILED
                item.error = str(exc)
            self._notify()
            if on_error:
                on_error(str(exc))

    def _notify(self) -> None:
        if self._on_queue_changed:
            self._on_queue_changed(self.snapshot())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filename_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    name = path.rsplit("/", 1)[-1] or "roulette_download"
    return urllib.parse.unquote(name)
