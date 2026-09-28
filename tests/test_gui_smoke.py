import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow
from app.gui.widgets.panels import DownloadSettings, GeminiPanel
from app.models.commands import DownloadIntent


def _app():
    return QApplication.instance() or QApplication([])


def test_reference_shell_geometry():
    app=_app();w=MainWindow();w.resize(1672,941);w.show();app.processEvents();sizes=w.splitter.sizes();assert abs(sizes[0]-205)<=16;assert abs(sizes[2]-391)<=20;assert w.ai.isVisible();w.close()


def test_gemini_enter_submits_but_shift_enter_adds_line():
    app=_app();panel=GeminiPanel();sent=[];panel.send.connect(sent.append);panel.input.setPlainText("cek dulu berapa video");panel.input.setFocus();QTest.keyClick(panel.input,Qt.Key_Return);app.processEvents();assert sent==["cek dulu berapa video"]
    panel.input.setPlainText("baris satu");panel.input.moveCursor(QTextCursor.End);QTest.keyClick(panel.input,Qt.Key_Return,Qt.ShiftModifier);app.processEvents();assert "\n" in panel.input.toPlainText()


def test_settings_load_intent_syncs_formats_without_emitting_changes(tmp_path):
    _app();settings=DownloadSettings();changes=[];settings.changed.connect(changes.append);intent=DownloadIntent(mode="audio",video_format="mkv",audio_format="opus",concurrent_downloads=7,output_folder=str(tmp_path));settings.load_intent(intent);assert settings.video.currentText()=="MKV";assert settings.audio.currentText()=="Opus";assert settings.parallel.value()==7;assert settings.folder.text()==str(tmp_path);assert not changes
