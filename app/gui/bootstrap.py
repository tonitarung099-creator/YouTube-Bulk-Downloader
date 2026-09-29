from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow


def run_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Pengunduh YouTube Massal")
    window = MainWindow()
    app.aboutToQuit.connect(window.controller.shutdown)
    window.show()
    return app.exec()
