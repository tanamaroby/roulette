"""
settings_panel.py
-----------------
A collapsible panel exposing common mpv flags as toggle/spinbox controls.

Each control maps 1-to-1 to a field in ``MpvFlags``.  Adding a new control
only requires adding a widget here and updating ``get_flags()``.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.core.player import MpvFlags


class SettingsPanel(QWidget):
    """Exposes mpv flags as UI controls and returns an ``MpvFlags`` instance."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(16)

        # ── Playback group ────────────────────────────────────────────
        pb_group = QGroupBox("Playback")
        pb_group.setObjectName("settingsGroup")
        pb_form = QFormLayout(pb_group)
        pb_form.setSpacing(16)
        pb_form.setContentsMargins(16, 24, 16, 20)
        pb_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pb_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.chk_fullscreen = QCheckBox()
        self.chk_fullscreen.setChecked(True)
        pb_form.addRow("Fullscreen", self.chk_fullscreen)

        self.chk_shuffle = QCheckBox()
        self.chk_shuffle.setChecked(True)
        pb_form.addRow("Shuffle", self.chk_shuffle)

        self.cmb_loop_playlist = QComboBox()
        self.cmb_loop_playlist.addItems(["inf (loop forever)", "no (play once)", "force"])
        self.cmb_loop_playlist.setCurrentIndex(0)
        pb_form.addRow("Loop Playlist", self.cmb_loop_playlist)

        self.cmb_loop_file = QComboBox()
        self.cmb_loop_file.addItems(["no", "inf (loop single file)"])
        self.cmb_loop_file.setCurrentIndex(0)
        pb_form.addRow("Loop File", self.cmb_loop_file)

        self.spn_volume = QSlider(Qt.Orientation.Horizontal)
        self.spn_volume.setRange(0, 130)
        self.spn_volume.setValue(100)
        volume_row = QHBoxLayout()
        volume_row.addWidget(self.spn_volume)
        self._vol_label = QLabel("100")
        self._vol_label.setFixedWidth(32)
        volume_row.addWidget(self._vol_label)
        self.spn_volume.valueChanged.connect(lambda v: self._vol_label.setText(str(v)))
        pb_form.addRow("Volume", volume_row)  # type: ignore[arg-type]

        self.spn_speed = QDoubleSpinBox()
        self.spn_speed.setRange(0.25, 4.0)
        self.spn_speed.setSingleStep(0.25)
        self.spn_speed.setValue(1.0)
        pb_form.addRow("Speed", self.spn_speed)

        self.chk_mute = QCheckBox()
        pb_form.addRow("Mute", self.chk_mute)

        layout.addWidget(pb_group)

        # ── Video group ───────────────────────────────────────────────
        vid_group = QGroupBox("Video")
        vid_group.setObjectName("settingsGroup")
        vid_form = QFormLayout(vid_group)
        vid_form.setSpacing(16)
        vid_form.setContentsMargins(16, 24, 16, 20)
        vid_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        vid_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.cmb_hwdec = QComboBox()
        self.cmb_hwdec.addItems(["auto", "videotoolbox", "no"])
        vid_form.addRow("HW Decoding", self.cmb_hwdec)

        self.cmb_sub_auto = QComboBox()
        self.cmb_sub_auto.addItems(["fuzzy", "exact", "all", "no"])
        vid_form.addRow("Subtitle Auto-load", self.cmb_sub_auto)

        self.chk_ontop = QCheckBox()
        vid_form.addRow("Always on Top", self.chk_ontop)

        self.chk_no_border = QCheckBox()
        vid_form.addRow("Borderless Window", self.chk_no_border)

        layout.addWidget(vid_group)

        # ── Extra flags ───────────────────────────────────────────────
        ext_group = QGroupBox("Extra mpv Flags")
        ext_group.setObjectName("settingsGroup")
        ext_layout = QVBoxLayout(ext_group)
        ext_layout.setContentsMargins(16, 24, 16, 20)
        ext_layout.setSpacing(10)
        hint = QLabel("Space-separated raw flags passed directly to mpv")
        hint.setObjectName("hintLabel")
        ext_layout.addWidget(hint)
        self.txt_extra = QLineEdit()
        self.txt_extra.setPlaceholderText("e.g.  --no-osc  --vo=gpu")
        ext_layout.addWidget(self.txt_extra)
        layout.addWidget(ext_group)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_flags(self) -> MpvFlags:
        loop_map = {"inf (loop forever)": "inf", "no (play once)": "no", "force": "force"}
        loop_file_map = {"no": "no", "inf (loop single file)": "inf"}

        extra_raw = self.txt_extra.text().strip().split()

        return MpvFlags(
            fullscreen=self.chk_fullscreen.isChecked(),
            shuffle=self.chk_shuffle.isChecked(),
            loop_playlist=loop_map.get(self.cmb_loop_playlist.currentText(), "inf"),
            loop_file=loop_file_map.get(self.cmb_loop_file.currentText(), "no"),
            volume=self.spn_volume.value(),
            speed=self.spn_speed.value(),
            mute=self.chk_mute.isChecked(),
            hwdec=self.cmb_hwdec.currentText(),
            sub_auto=self.cmb_sub_auto.currentText(),
            ontop=self.chk_ontop.isChecked(),
            no_border=self.chk_no_border.isChecked(),
            extra_flags=extra_raw,
        )

    def set_flags(self, flags: MpvFlags) -> None:
        """Populate controls from an existing ``MpvFlags`` instance."""
        self.chk_fullscreen.setChecked(flags.fullscreen)
        self.chk_shuffle.setChecked(flags.shuffle)
        loop_text = {"inf": "inf (loop forever)", "no": "no (play once)", "force": "force"}
        idx = self.cmb_loop_playlist.findText(loop_text.get(flags.loop_playlist, "inf (loop forever)"))
        if idx >= 0:
            self.cmb_loop_playlist.setCurrentIndex(idx)
        loop_file_text = {"no": "no", "inf": "inf (loop single file)"}
        idx2 = self.cmb_loop_file.findText(loop_file_text.get(flags.loop_file, "no"))
        if idx2 >= 0:
            self.cmb_loop_file.setCurrentIndex(idx2)
        self.spn_volume.setValue(flags.volume)
        self.spn_speed.setValue(flags.speed)
        self.chk_mute.setChecked(flags.mute)
        idx3 = self.cmb_hwdec.findText(flags.hwdec)
        if idx3 >= 0:
            self.cmb_hwdec.setCurrentIndex(idx3)
        idx4 = self.cmb_sub_auto.findText(flags.sub_auto)
        if idx4 >= 0:
            self.cmb_sub_auto.setCurrentIndex(idx4)
        self.chk_ontop.setChecked(flags.ontop)
        self.chk_no_border.setChecked(flags.no_border)
        self.txt_extra.setText(" ".join(flags.extra_flags))
