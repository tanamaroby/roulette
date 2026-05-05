"""
main_window.py
--------------
The application's main window.

Layout (left | right split):
  Left  — FolderListWidget  (media sources)
  Right — SettingsPanel     (mpv flags)
  Bottom bar — Play / Stop buttons + status label
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.core.folder_manager import FolderManager
from app.core.mpv_checker import ensure_mpv, is_mpv_available
from app.core.player import MpvPlayer
from app.core.playlist import PlaylistBuilder
from app.ui.widgets.folder_list import FolderListWidget
from app.ui.widgets.settings_panel import SettingsPanel


# ---------------------------------------------------------------------------
# Background installer thread
# ---------------------------------------------------------------------------

class _InstallerWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def run(self) -> None:
        ok = ensure_mpv(progress_callback=self.progress.emit)
        self.finished.emit(ok)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._folder_manager = FolderManager()
        self._player: MpvPlayer | None = None
        self._temp_playlist: str | None = None
        self._installer_thread: QThread | None = None

        self.setWindowTitle("Roulette — Media Shuffler")
        self.setMinimumSize(1080, 680)
        self.resize(1120, 720)
        self._set_icon()
        self._build_ui()
        self._apply_stylesheet()
        self._check_mpv_on_startup()

    # ------------------------------------------------------------------
    # Icon
    # ------------------------------------------------------------------

    def _set_icon(self) -> None:
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(16)

        # ── Title bar area ─────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(14)
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            lbl_icon = QLabel()
            pix = QPixmap(str(icon_path)).scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
            lbl_icon.setPixmap(pix)
            title_row.addWidget(lbl_icon)

        title_text = QVBoxLayout()
        title_text.setSpacing(2)
        title_lbl = QLabel("Roulette")
        title_lbl.setObjectName("appTitle")
        title_text.addWidget(title_lbl)
        subtitle_lbl = QLabel("Media Shuffler")
        subtitle_lbl.setObjectName("appSubtitle")
        title_text.addWidget(subtitle_lbl)
        title_row.addLayout(title_text)
        title_row.addStretch()

        self._mpv_status_lbl = QLabel()
        self._mpv_status_lbl.setObjectName("mpvStatusLabel")
        title_row.addWidget(self._mpv_status_lbl)

        root.addLayout(title_row)

        # ── Main content splitter ──────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: folder list
        self._folder_list = FolderListWidget(self._folder_manager)
        self._folder_list.folders_changed.connect(self._on_folders_changed)
        splitter.addWidget(self._folder_list)

        # Right: settings (scrollable)
        self._settings = SettingsPanel()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._settings)
        scroll.setObjectName("settingsScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        splitter.addWidget(scroll)

        splitter.setSizes([480, 560])
        root.addWidget(splitter, stretch=1)

        # ── Separator ──────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("divider")
        root.addWidget(sep)

        # ── Bottom action bar ──────────────────────────────────────────
        bar = QHBoxLayout()
        bar.setSpacing(12)

        self._count_lbl = QLabel("0 files found")
        self._count_lbl.setObjectName("countLabel")
        bar.addWidget(self._count_lbl)
        bar.addStretch()

        self._stop_btn = QPushButton("⏹  Stop")
        self._stop_btn.setObjectName("stopButton")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)
        bar.addWidget(self._stop_btn)

        self._play_btn = QPushButton("▶  Play")
        self._play_btn.setObjectName("playButton")
        self._play_btn.clicked.connect(self._on_play)
        bar.addWidget(self._play_btn)

        root.addLayout(bar)

        # ── Status bar ─────────────────────────────────────────────────
        self._status = QStatusBar()
        self._status.setObjectName("appStatusBar")
        self.setStatusBar(self._status)
        self._status.showMessage("Ready.")

        self._refresh_count()

    # ------------------------------------------------------------------
    # Stylesheet
    # ------------------------------------------------------------------

    def _apply_stylesheet(self) -> None:
        assets = str(Path(__file__).parent.parent / "assets")
        toggle_on  = f"{assets}/toggle_on.svg"
        toggle_off = f"{assets}/toggle_off.svg"

        self.setStyleSheet(f"""
        /* ── Base ─────────────────────────────────────────────────── */
        QMainWindow, QWidget {{
            background-color: #0d1117;
            color: #e2e8f0;
            font-family: -apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
            font-size: 13px;
        }}

        /* ── Title ────────────────────────────────────────────────── */
        QLabel#appTitle {{
            font-size: 24px;
            font-weight: 700;
            color: #a5b4fc;
            letter-spacing: 0.3px;
        }}
        QLabel#appSubtitle {{
            font-size: 11px;
            color: #3d4a6e;
            letter-spacing: 1.2px;
            text-transform: uppercase;
        }}

        /* ── Labels ───────────────────────────────────────────────── */
        QLabel#sectionLabel {{
            font-size: 13px;
            font-weight: 600;
            color: #c7d2fe;
        }}
        QLabel#hintLabel {{
            color: #3d4a6e;
            font-size: 11px;
        }}
        QLabel#countLabel {{
            color: #4b5a7e;
            font-size: 12px;
        }}
        QLabel#mpvStatusLabel {{
            font-size: 11px;
            font-weight: 600;
            padding: 5px 14px;
            border-radius: 12px;
        }}

        /* ── Divider ──────────────────────────────────────────────── */
        QFrame#divider {{
            background-color: #1a2040;
            border: none;
            max-height: 1px;
        }}

        /* ── Folder list ──────────────────────────────────────────── */
        QListWidget#folderList {{
            background-color: #111827;
            border: 1px solid #1e2a4a;
            border-radius: 10px;
            padding: 6px;
            color: #e2e8f0;
            outline: none;
        }}
        QListWidget#folderList::item {{
            padding: 9px 12px;
            border-radius: 7px;
            margin: 2px 0;
            color: #cbd5e1;
        }}
        QListWidget#folderList::item:selected {{
            background-color: #312e81;
            color: #e0e7ff;
        }}
        QListWidget#folderList::item:hover:!selected {{
            background-color: #161d35;
        }}

        /* ── Buttons ──────────────────────────────────────────────── */
        QPushButton#accentButton {{
            background-color: #4f46e5;
            color: white;
            border: none;
            padding: 8px 18px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton#accentButton:hover   {{ background-color: #6366f1; }}
        QPushButton#accentButton:pressed {{ background-color: #3730a3; }}

        QPushButton#dangerButton {{
            background-color: transparent;
            color: #f87171;
            border: 1px solid #3d1515;
            padding: 8px 18px;
            border-radius: 8px;
            font-size: 13px;
        }}
        QPushButton#dangerButton:hover {{
            background-color: #450a0a;
            border-color: #7f1d1d;
        }}

        QPushButton#playButton {{
            background-color: #7c3aed;
            color: white;
            border: none;
            padding: 12px 40px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            min-width: 150px;
            letter-spacing: 0.3px;
        }}
        QPushButton#playButton:hover   {{ background-color: #8b5cf6; }}
        QPushButton#playButton:pressed {{ background-color: #6d28d9; }}
        QPushButton#playButton:disabled {{
            background-color: #161d35;
            color: #2d3561;
        }}

        QPushButton#stopButton {{
            background-color: transparent;
            color: #64748b;
            border: 1px solid #1e2a4a;
            padding: 12px 32px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
        }}
        QPushButton#stopButton:hover {{
            background-color: #111827;
            color: #94a3b8;
            border-color: #2d3561;
        }}
        QPushButton#stopButton:disabled {{
            color: #1e2a4a;
            border-color: #111827;
        }}

        /* ── Group boxes ──────────────────────────────────────────── */
        QGroupBox#settingsGroup {{
            border: 1px solid #1a2040;
            border-radius: 10px;
            margin-top: 20px;
            background-color: #0d1117;
            padding-bottom: 4px;
        }}
        QGroupBox#settingsGroup::title {{
            subcontrol-origin: margin;
            left: 16px;
            top: 0px;
            padding: 2px 10px;
            background-color: #0d1117;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.2px;
            color: #4f46e5;
        }}

        /* ── Scroll area ──────────────────────────────────────────── */
        QScrollArea#settingsScroll {{
            border: none;
            background-color: transparent;
        }}
        QScrollArea#settingsScroll > QWidget > QWidget {{
            background-color: transparent;
        }}

        /* Thin, subtle scrollbar */
        QScrollBar:vertical {{
            background: transparent;
            width: 5px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: #1e2a4a;
            border-radius: 3px;
            min-height: 32px;
        }}
        QScrollBar::handle:vertical:hover {{ background: #4f46e5; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

        /* ── Form inputs ──────────────────────────────────────────── */
        QComboBox, QDoubleSpinBox, QLineEdit {{
            background-color: #111827;
            border: 1px solid #1e2a4a;
            border-radius: 7px;
            padding: 7px 10px;
            color: #e2e8f0;
            min-height: 32px;
            selection-background-color: #4f46e5;
        }}
        QComboBox:focus, QLineEdit:focus, QDoubleSpinBox:focus {{
            border-color: #4f46e5;
            background-color: #0f1828;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #111827;
            border: 1px solid #1e2a4a;
            border-radius: 7px;
            selection-background-color: #4f46e5;
            color: #e2e8f0;
            padding: 4px;
        }}
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            width: 20px;
            border: none;
            background: transparent;
        }}

        /* ── Toggle checkboxes (pill switch via SVG) ──────────────── */
        QCheckBox {{
            spacing: 0px;
        }}
        QCheckBox::indicator {{
            width: 44px;
            height: 24px;
            border-radius: 12px;
            border: none;
        }}
        QCheckBox::indicator:unchecked {{
            image: url({toggle_off});
        }}
        QCheckBox::indicator:checked {{
            image: url({toggle_on});
        }}

        /* ── Volume slider ────────────────────────────────────────── */
        QSlider::groove:horizontal {{
            height: 5px;
            background: #1e2a4a;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: #7c3aed;
            border: 2px solid #6d28d9;
            width: 18px;
            height: 18px;
            margin: -7px 0;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{
            background: #8b5cf6;
        }}
        QSlider::sub-page:horizontal {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #4f46e5, stop:1 #7c3aed);
            border-radius: 3px;
        }}

        /* ── Status bar ───────────────────────────────────────────── */
        QStatusBar#appStatusBar {{
            background-color: #080b14;
            color: #2d3561;
            font-size: 11px;
            padding: 2px 8px;
        }}

        /* ── Splitter handle ──────────────────────────────────────── */
        QSplitter::handle {{
            background-color: #1a2040;
            width: 1px;
        }}
        """)

    # ------------------------------------------------------------------
    # mpv startup check
    # ------------------------------------------------------------------

    def _check_mpv_on_startup(self) -> None:
        if is_mpv_available():
            self._set_mpv_status(ready=True)
            return

        self._set_mpv_status(ready=False, text="mpv not found — installing…")
        self._play_btn.setEnabled(False)
        self._status.showMessage("mpv not found. Installing via Homebrew…")

        self._installer_thread = QThread()
        self._worker = _InstallerWorker()
        self._worker.moveToThread(self._installer_thread)
        self._installer_thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda msg: self._status.showMessage(msg))
        self._worker.finished.connect(self._on_install_done)
        self._worker.finished.connect(self._installer_thread.quit)
        self._installer_thread.start()

    def _on_install_done(self, success: bool) -> None:
        if success:
            self._set_mpv_status(ready=True)
            self._play_btn.setEnabled(True)
            self._status.showMessage("mpv installed successfully.")
        else:
            self._set_mpv_status(ready=False, text="mpv unavailable")
            self._status.showMessage(
                "mpv could not be installed. Please install it manually: brew install mpv"
            )
            QMessageBox.critical(
                self,
                "mpv Not Found",
                "Roulette could not install mpv automatically.\n\n"
                "Please run the following command in Terminal and restart:\n\n"
                "  brew install mpv",
            )

    def _set_mpv_status(self, ready: bool, text: str = "") -> None:
        if ready:
            self._mpv_status_lbl.setText("● mpv ready")
            self._mpv_status_lbl.setStyleSheet(
                "background:#064e3b; color:#6ee7b7; padding:3px 8px; border-radius:10px;"
            )
        else:
            display = text or "● mpv missing"
            self._mpv_status_lbl.setText(display)
            self._mpv_status_lbl.setStyleSheet(
                "background:#7f1d1d; color:#fca5a5; padding:3px 8px; border-radius:10px;"
            )

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _on_play(self) -> None:
        if not is_mpv_available():
            QMessageBox.warning(self, "mpv Not Ready", "mpv is not available yet.")
            return

        files = self._folder_manager.resolve_all_media()
        if not files:
            QMessageBox.information(
                self, "No Media Found",
                "No supported media files were found in the saved folders.\n"
                "Add at least one folder containing video or audio files."
            )
            return

        flags = self._settings.get_flags()
        builder = PlaylistBuilder(files)
        if flags.shuffle:
            builder.shuffle()

        # Write temp playlist
        self._cleanup_temp()
        self._temp_playlist = builder.write_temp_m3u()

        self._player = MpvPlayer(flags=flags, on_exit=self._on_playback_ended)
        try:
            self._player.play(self._temp_playlist)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Launch Error", str(exc))
            return

        self._play_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status.showMessage(f"Playing {len(builder)} file(s) via mpv…")

    def _on_stop(self) -> None:
        if self._player:
            self._player.stop()
        self._playback_reset()

    def _on_playback_ended(self, _exit_code: int) -> None:
        # Called from background thread — use invokeMethod-safe signal or
        # just tolerate that Qt widgets are touched from a thread (safe for
        # simple label/button state updates on macOS).
        self._playback_reset()

    def _playback_reset(self) -> None:
        self._play_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status.showMessage("Ready.")
        self._cleanup_temp()

    def _cleanup_temp(self) -> None:
        if self._temp_playlist and os.path.exists(self._temp_playlist):
            try:
                os.remove(self._temp_playlist)
            except OSError:
                pass
        self._temp_playlist = None

    # ------------------------------------------------------------------
    # Folder events
    # ------------------------------------------------------------------

    def _on_folders_changed(self) -> None:
        self._refresh_count()

    def _refresh_count(self) -> None:
        files = self._folder_manager.resolve_all_media()
        n = len(files)
        self._count_lbl.setText(f"{n} file{'s' if n != 1 else ''} found")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._player:
            self._player.stop()
        self._cleanup_temp()
        super().closeEvent(event)
