"""
rule34_resolver.py
------------------
Resolves rule34.xxx tag searches into direct video URLs using the
public JSON API (https://api.rule34.xxx).

API authentication
~~~~~~~~~~~~~~~~~~
A free API key is required. Obtain one at:
  https://rule34.xxx/index.php?page=account&s=options

Extensibility note
~~~~~~~~~~~~~~~~~~
``Rule34Resolver`` subclasses ``MediaResolver`` — it slots into
``PlaylistBuilder`` the same way local folder results do.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Callable

from app.core.folder_manager import MediaResolver

_API_BASE = "https://api.rule34.xxx/index.php"
_PAGE_LIMIT = 100          # rule34 hard-caps at 1 000; 100 is safe and polite
_VIDEO_EXTS = frozenset({".mp4", ".webm", ".mkv", ".mov", ".avi", ".flv"})
_UA = "Roulette-MediaShuffler/1.0"


class Rule34Resolver(MediaResolver):
    """
    Fetches posts from rule34.xxx matching ``tags`` and returns the
    highest-quality direct ``file_url`` for every video post found.

    Parameters
    ----------
    tags:
        Space-separated rule34 tags (supports all meta-tags and
        operators, e.g. ``video score:>100 order:score``).
    max_results:
        Upper bound on the number of video URLs returned (≤ 1 000).
    user_id:
        Numeric account ID (shown on the rule34.xxx account page).
    api_key:
        API key obtained from https://rule34.xxx/index.php?page=account&s=options
    progress_callback:
        Optional callable(str) for status messages (used by the UI).
    """

    def __init__(
        self,
        tags: str = "video",
        max_results: int = 200,
        user_id: str = "",
        api_key: str = "",
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.tags = tags.strip() or "video"
        self.max_results = max(1, min(max_results, 1000))
        self.user_id = user_id.strip()
        self.api_key = api_key.strip()
        self.progress_callback = progress_callback

    # ------------------------------------------------------------------
    # MediaResolver interface
    # ------------------------------------------------------------------

    def resolve(self, source: str = "") -> list[str]:
        """
        Fetch pages from the API until ``max_results`` video URLs are
        collected (or results are exhausted).

        The ``source`` parameter is unused — ``tags`` drives the query.
        """
        urls: list[str] = []
        page = 0

        while len(urls) < self.max_results:
            self._log(f"Fetching page {page + 1}…")
            batch = self._fetch_page(page)
            if not batch:
                break

            for post in batch:
                file_url: str = post.get("file_url", "")
                if file_url and _is_video_url(file_url):
                    urls.append(file_url)
                if len(urls) >= self.max_results:
                    break

            if len(batch) < _PAGE_LIMIT:
                break  # no further pages
            page += 1

        self._log(f"Done — {len(urls)} video(s) found.")
        return urls

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_page(self, page: int) -> list[dict]:
        params: dict[str, str | int] = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": self.tags,
            "limit": _PAGE_LIMIT,
            "pid": page,
            "json": 1,
        }
        if self.user_id and self.api_key:
            params["user_id"] = self.user_id
            params["api_key"] = self.api_key

        url = f"{_API_BASE}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            parsed = json.loads(data)
            return parsed if isinstance(parsed, list) else []
        except Exception as exc:
            self._log(f"API error (page {page}): {exc}")
            return []

    def _log(self, msg: str) -> None:
        if self.progress_callback:
            self.progress_callback(msg)


# ---------------------------------------------------------------------------
# Helpers (module-level so they can be tested independently)
# ---------------------------------------------------------------------------

def _is_video_url(url: str) -> bool:
    """Return True if the URL points to a recognised video format."""
    path = url.lower().split("?")[0]
    return any(path.endswith(ext) for ext in _VIDEO_EXTS)
