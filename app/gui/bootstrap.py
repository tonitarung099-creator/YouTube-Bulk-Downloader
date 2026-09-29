from __future__ import annotations

import sys
import threading
import traceback
from datetime import datetime, timezone

from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.paths import data_dir
from app.gui.main_window import MainWindow


def _write_crash_log(exc_type, exc_value, exc_tb) -> str:
    path = data_dir() / "crash.log"
    stamp = datetime.now(timezone.utc).isoformat()
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{stamp}]\n{text}\n")
    except Exception:
        pass
    return str(path)


def _install_exception_guard() -> None:
    def handle(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log_path = _write_crash_log(exc_type, exc_value, exc_tb)
        try:
            QMessageBox.critical(
                None,
                "Terjadi Kesalahan",
                "Aplikasi mengalami error, tetapi detailnya sudah disimpan agar tidak hilang diam-diam.\n\n"
                f"Log: {log_path}\n\n{str(exc_value)[:500]}",
            )
        except Exception:
            pass

    sys.excepthook = handle

    def thread_handle(args: threading.ExceptHookArgs):
        _write_crash_log(args.exc_type, args.exc_value, args.exc_traceback)

    threading.excepthook = thread_handle


def run_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Pengunduh YouTube Massal")
    _install_exception_guard()
    window = MainWindow()
    app.aboutToQuit.connect(window.controller.shutdown)
    window.show()
    return app.exec()
