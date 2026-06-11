"""
download_queue.py
-----------------
A non-modal dialog that shows the live download queue.

It is driven entirely by ``refresh(queue)`` calls from the main window;
no background threads run here.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.downloader import DownloadItem, DownloadState

_STATE_ICON = {
    DownloadState.QUEUED:      "\u23f3",   # ⏳
    DownloadState.DOWNLOADING: "\u2b07\ufe0f",  # ⬇️
    DownloadState.DONE:        "\u2705",   # ✅
    DownloadState.FAILED:      "\u274c",   # ❌
}

_STATE_COLOUR = {
    DownloadState.QUEUED:      "#64748b",
    DownloadState.DOWNLOADING: "#a5b4fc",
    DownloadState.DONE:        "#6ee7b7",
    DownloadState.FAILED:      "#f87171",
}


class DownloadQueueDialog(QDialog):
    """
    Non-modal window listing every download item and its current state.
    Stays open across multiple calls to ``refresh()``.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("Downloads")
        self.setMinimumSize(520, 320)
        self._build_ui()
        self._apply_stylesheet()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh(self, queue: list[DownloadItem]) -> None:
        """Repopulate the list from *queue* (called from the main thread)."""
        self._list.clear()
        self._summary_lbl.setText(self._summary(queue))
        for item in reversed(queue):      # newest at top
            icon = _STATE_ICON[item.state]
            colour = _STATE_COLOUR[item.state]
            if item.state == DownloadState.DONE:
                detail = Path(item.dest).parent.name
            elif item.state == DownloadState.FAILED:
                detail = item.error[:60]
            elif item.state == DownloadState.DOWNLOADING:
                detail = "downloading\u2026"
            else:
                detail = "queued"
            text = f"{icon}  {item.filename}\n     {detail}"
            li = QListWidgetItem(text)
            li.setForeground(
                __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(colour)
            )
            li.setToolTip(item.url)
            self._list.addItem(li)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self._summary_lbl = QLabel("No downloads yet.")
        self._summary_lbl.setObjectName("dlSummaryLabel")
        root.addWidget(self._summary_lbl)

        self._list = QListWidget()
        self._list.setObjectName("dlList")
        self._list.setSpacing(2)
        root.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("stopButton")
        close_btn.clicked.connect(self.hide)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet("""
        QDialog {
            background-color: #0d1117;
            color: #e2e8f0;
            font-family: ".AppleSystemUIFont", "SF Pro Text", Arial, sans-serif;
            font-size: 13px;
        }
        QLabel#dlSummaryLabel {
            color: #64748b;
            font-size: 12px;
        }
        QListWidget#dlList {
            background-color: #111827;
            border: 1px solid #1e2a4a;
            border-radius: 10px;
            padding: 6px;
            color: #e2e8f0;
            outline: none;
        }
        QListWidget#dlList::item {
            padding: 8px 10px;
            border-radius: 7px;
            margin: 2px 0;
            line-height: 1.5;
        }
        QListWidget#dlList::item:selected {
            background-color: #1e2a4a;
        }
        QPushButton#stopButton {
            background-color: transparent;
            color: #64748b;
            border: 1px solid #1e2a4a;
            padding: 8px 24px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton#stopButton:hover {
            background-color: #111827;
            color: #94a3b8;
            border-color: #2d3561;
        }
        """)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _summary(queue: list[DownloadItem]) -> str:
        if not queue:
            return "No downloads yet."
        active = sum(1 for i in queue if i.state == DownloadState.DOWNLOADING)
        done   = sum(1 for i in queue if i.state == DownloadState.DONE)
        failed = sum(1 for i in queue if i.state == DownloadState.FAILED)
        queued = sum(1 for i in queue if i.state == DownloadState.QUEUED)
        parts: list[str] = []
        if active:
            parts.append(f"{active} downloading")
        if queued:
            parts.append(f"{queued} queued")
        if done:
            parts.append(f"{done} done")
        if failed:
            parts.append(f"{failed} failed")
        return "  \u00b7  ".join(parts)
