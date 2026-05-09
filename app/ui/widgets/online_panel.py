"""
online_panel.py
---------------
UI panel for fetching media from online sources.

Currently supports: R4 (via R4Resolver).

Credentials (user_id + api_key) are persisted to
~/.config/roulette/r4.json so the user only types them once.
"""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.r4_resolver import R4Resolver

_CREDS_FILE = Path.home() / ".config" / "roulette" / "r4.json"


# ---------------------------------------------------------------------------
# Background fetch worker
# ---------------------------------------------------------------------------

class _FetchWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, tags: str, max_results: int, user_id: str, api_key: str) -> None:
        super().__init__()
        self._tags = tags
        self._max = max_results
        self._user_id = user_id
        self._api_key = api_key

    def run(self) -> None:
        resolver = R4Resolver(
            tags=self._tags,
            max_results=self._max,
            user_id=self._user_id,
            api_key=self._api_key,
            progress_callback=self.progress.emit,
        )
        self.finished.emit(resolver.resolve())


# ---------------------------------------------------------------------------
# Panel widget
# ---------------------------------------------------------------------------

class OnlinePanel(QWidget):
    """
    Lets the user configure and fetch from R4.
    Call ``get_urls()`` to retrieve the last fetched list.
    """

    urls_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._urls: list[str] = []
        self._thread: QThread | None = None
        self._worker: _FetchWorker | None = None
        self._build_ui()
        self._load_creds()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_urls(self) -> list[str]:
        return list(self._urls)

    # ------------------------------------------------------------------
    # UI build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # ── Credentials ────────────────────────────────────────────────
        cred_group = QGroupBox("R4 Authentication")
        cred_group.setObjectName("settingsGroup")
        cred_layout = QVBoxLayout(cred_group)
        cred_layout.setContentsMargins(16, 24, 16, 16)
        cred_layout.setSpacing(16)

        uid_row = QHBoxLayout()
        uid_row.setSpacing(12)
        uid_lbl = QLabel("User ID")
        uid_lbl.setObjectName("formLabel")
        uid_lbl.setFixedWidth(76)
        self._uid_input = QLineEdit()
        self._uid_input.setPlaceholderText("Your numeric account ID")
        uid_row.addWidget(uid_lbl)
        uid_row.addWidget(self._uid_input)
        cred_layout.addLayout(uid_row)

        key_row = QHBoxLayout()
        key_row.setSpacing(12)
        key_lbl = QLabel("API Key")
        key_lbl.setObjectName("formLabel")
        key_lbl.setFixedWidth(76)
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("Paste your API key here")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_row.addWidget(key_lbl)
        key_row.addWidget(self._key_input)
        cred_layout.addLayout(key_row)

        get_key_btn = QPushButton("Get API key →")
        get_key_btn.setObjectName("linkButton")
        get_key_btn.setFlat(True)
        get_key_btn.setCursor(
            __import__("PyQt6.QtGui", fromlist=["QCursor"]).QCursor(
                __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor
            )
        )
        get_key_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://rule34.xxx/index.php?page=account&s=options")
            )
        )
        cred_layout.addWidget(get_key_btn)
        root.addWidget(cred_group)

        # ── Query ──────────────────────────────────────────────────────
        q_group = QGroupBox("Query")
        q_group.setObjectName("settingsGroup")
        q_layout = QVBoxLayout(q_group)
        q_layout.setContentsMargins(16, 24, 16, 16)
        q_layout.setSpacing(16)

        tags_row = QHBoxLayout()
        tags_row.setSpacing(12)
        tags_lbl = QLabel("Tags")
        tags_lbl.setObjectName("formLabel")
        tags_lbl.setFixedWidth(76)
        self._tags_input = QLineEdit()
        self._tags_input.setText("video")
        self._tags_input.setPlaceholderText("video  score:>100  order:score  -tag")
        tags_row.addWidget(tags_lbl)
        tags_row.addWidget(self._tags_input)
        q_layout.addLayout(tags_row)

        max_row = QHBoxLayout()
        max_row.setSpacing(12)
        max_lbl = QLabel("Max Results")
        max_lbl.setObjectName("formLabel")
        max_lbl.setFixedWidth(76)
        self._max_spin = QSpinBox()
        self._max_spin.setRange(1, 1000)
        self._max_spin.setValue(200)
        self._max_spin.setSuffix(" videos")
        max_row.addWidget(max_lbl)
        max_row.addWidget(self._max_spin)
        max_row.addStretch()
        q_layout.addLayout(max_row)

        tag_hint = QLabel(
            "Space-separated. Supports meta-tags: score:>N, order:score, rating:e, -tag_to_exclude"
        )
        tag_hint.setObjectName("hintLabel")
        tag_hint.setWordWrap(True)
        q_layout.addWidget(tag_hint)
        root.addWidget(q_group)

        # ── Fetch button ───────────────────────────────────────────────
        self._fetch_btn = QPushButton("↓  Fetch from R4")
        self._fetch_btn.setObjectName("fetchButton")
        self._fetch_btn.clicked.connect(self._on_fetch)
        root.addWidget(self._fetch_btn)

        # ── Status ─────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("divider")
        root.addWidget(sep)

        self._status_lbl = QLabel("No results yet — enter your credentials and click Fetch.")
        self._status_lbl.setObjectName("onlineStatusLabel")
        self._status_lbl.setWordWrap(True)
        root.addWidget(self._status_lbl)

        warn = QLabel(
            "\u26a0\ufe0f  Adult content site. Ensure you comply with all applicable local laws."
        )
        warn.setObjectName("warnLabel")
        warn.setWordWrap(True)
        root.addWidget(warn)

        root.addStretch()

    # ------------------------------------------------------------------
    # Credentials persistence
    # ------------------------------------------------------------------

    def _load_creds(self) -> None:
        if not _CREDS_FILE.exists():
            return
        try:
            data = json.loads(_CREDS_FILE.read_text(encoding="utf-8"))
            self._uid_input.setText(data.get("user_id", ""))
            self._key_input.setText(data.get("api_key", ""))
            self._tags_input.setText(data.get("last_tags", "video"))
            self._max_spin.setValue(int(data.get("max_results", 200)))
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    def _save_creds(self) -> None:
        _CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CREDS_FILE.write_text(
            json.dumps(
                {
                    "user_id": self._uid_input.text().strip(),
                    "api_key": self._key_input.text().strip(),
                    "last_tags": self._tags_input.text().strip(),
                    "max_results": self._max_spin.value(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def _on_fetch(self) -> None:
        if self._thread and self._thread.isRunning():
            return

        user_id = self._uid_input.text().strip()
        api_key = self._key_input.text().strip()

        if not user_id or not api_key:
            self._status_lbl.setText(
                "Enter your User ID and API Key before fetching.\n"
                'Click "Get API key \u2192" above to open the account settings page.'
            )
            return

        self._save_creds()

        tags = self._tags_input.text().strip() or "video"
        max_results = self._max_spin.value()

        self._fetch_btn.setEnabled(False)
        self._fetch_btn.setText("Fetching…")
        self._urls = []
        self._status_lbl.setText("Connecting…")

        self._thread = QThread()
        self._worker = _FetchWorker(
            tags=tags, max_results=max_results, user_id=user_id, api_key=api_key
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._status_lbl.setText)
        self._worker.finished.connect(self._on_fetch_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_fetch_done(self, urls: list) -> None:
        self._urls = urls
        n = len(urls)
        if n:
            self._status_lbl.setText(f"\u25cf {n} video{'s' if n != 1 else ''} ready to play.")
        else:
            self._status_lbl.setText(
                "No videos found. Try different tags, or check your credentials."
            )
        self._fetch_btn.setEnabled(True)
        self._fetch_btn.setText("\u2193  Fetch from R4")
        self.urls_changed.emit()
