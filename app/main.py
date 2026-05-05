"""
main.py
-------
Application entry point.

Responsibilities:
  1. Generate the icon if it doesn't already exist.
  2. Launch the Qt application.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_icon() -> None:
    icon_path = Path(__file__).parent / "assets" / "icon.png"
    if not icon_path.exists():
        try:
            from app.assets.generate_icon import generate
            generate(str(icon_path))
        except Exception:
            pass  # Non-fatal; the icon is cosmetic.


def main() -> None:
    _ensure_icon()

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from app.ui.main_window import MainWindow

    # Enable high-DPI scaling (macOS Retina)
    app = QApplication(sys.argv)
    app.setApplicationName("Roulette")
    app.setOrganizationName("Roulette")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
