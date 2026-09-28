import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.gui.models.video_filter_proxy import VideoFilterProxyModel
from app.gui.models.video_table_model import VideoTableModel
from app.models.state import VideoItem


def test_search_and_kind_filter_are_combined():
    app = QApplication.instance() or QApplication([])
    model = VideoTableModel([
        VideoItem(id="1", title="Belajar Python", url="https://youtu.be/1", kind="Video"),
        VideoItem(id="2", title="Belajar Python Shorts", url="https://youtu.be/2", kind="Shorts", is_short=True),
        VideoItem(id="3", title="Berita Hari Ini", url="https://youtu.be/3", kind="Video"),
    ])
    proxy = VideoFilterProxyModel()
    proxy.setSourceModel(model)
    proxy.set_kind("Video")
    proxy.set_search("python")
    app.processEvents()
    assert proxy.rowCount() == 1
    assert proxy.index(0, 3).data() == "Belajar Python"
