import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow

def test_reference_shell_geometry():
    app=QApplication.instance() or QApplication([]);w=MainWindow();w.resize(1672,941);w.show();app.processEvents();sizes=w.splitter.sizes();assert abs(sizes[0]-205)<=16;assert abs(sizes[2]-391)<=20;assert w.ai.isVisible();w.close()
