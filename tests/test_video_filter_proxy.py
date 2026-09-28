import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableView

from app.gui.models.video_filter_proxy import VideoFilterProxyModel
from app.gui.models.video_table_model import VideoTableModel
from app.gui.widgets.checkable_header import CheckableHeader
from app.models.state import VideoItem


def _fixture():
    return VideoTableModel([
        VideoItem(id="1", title="Belajar Python", url="https://youtu.be/1", kind="Video"),
        VideoItem(id="2", title="Belajar Python Shorts", url="https://youtu.be/2", kind="Shorts", is_short=True),
        VideoItem(id="3", title="Berita Hari Ini", url="https://youtu.be/3", kind="Video"),
    ])


def test_search_and_kind_filter_are_combined():
    app = QApplication.instance() or QApplication([])
    model = _fixture();proxy = VideoFilterProxyModel();proxy.setSourceModel(model);proxy.set_kind("Video");proxy.set_search("python");app.processEvents()
    assert proxy.rowCount() == 1
    assert proxy.index(0, 3).data() == "Belajar Python"


def test_header_toggle_only_changes_visible_filtered_rows():
    app=QApplication.instance() or QApplication([]);model=_fixture();proxy=VideoFilterProxyModel();proxy.setSourceModel(model);proxy.set_kind("Video");proxy.set_search("python")
    table=QTableView();table.setModel(proxy);header=CheckableHeader(Qt.Horizontal,table);table.setHorizontalHeader(header);app.processEvents();assert proxy.rowCount()==1
    header.toggle_visible();app.processEvents()
    assert model.items[0].selected is False
    assert model.items[1].selected is True
    assert model.items[2].selected is True
    proxy.set_search("");app.processEvents();assert proxy.rowCount()==2;assert header._visible_state()==Qt.PartiallyChecked
