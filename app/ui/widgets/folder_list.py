"""
folder_list.py
--------------
A styled widget that displays the saved media folders and lets the user
add / remove them via drag-and-drop or a file-picker button.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.folder_manager import FolderManager


class FolderListWidget(QWidget):
    """
    Displays saved folders; emits ``folders_changed`` whenever the list
    is modified.
    """

    folders_changed = pyqtSignal()

    def __init__(self, folder_manager: FolderManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fm = folder_manager
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(10)
        lbl = QLabel("Media Folders")
        lbl.setObjectName("sectionLabel")
        header.addWidget(lbl)
        header.addStretch()

        add_btn = QPushButton("+ Add Folder")
        add_btn.setObjectName("accentButton")
        add_btn.clicked.connect(self._on_add)
        header.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self._on_remove)
        header.addWidget(remove_btn)

        layout.addLayout(header)

        # List
        self._list = QListWidget()
        self._list.setObjectName("folderList")
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._list)

        hint = QLabel('Drag & drop folders here, or click "Add Folder"')
        hint.setObjectName("hintLabel")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        if path:
            self._fm.add_folder(path)
            self._refresh()
            self.folders_changed.emit()

    def _on_remove(self) -> None:
        for item in self._list.selectedItems():
            self._fm.remove_folder(item.text())
        self._refresh()
        self.folders_changed.emit()

    def _refresh(self) -> None:
        self._list.clear()
        for folder in self._fm.folders:
            self._list.addItem(QListWidgetItem(folder))

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        changed = False
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if self._fm.add_folder(path):
                changed = True
        if changed:
            self._refresh()
            self.folders_changed.emit()
