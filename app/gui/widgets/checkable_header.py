from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtWidgets import QHeaderView, QStyle, QStyleOptionButton


class CheckableHeader(QHeaderView):
    """Checkbox header: hanya mengubah baris proxy yang sedang terlihat."""

    check_state_changed = Signal(object)

    def __init__(self, orientation=Qt.Horizontal, parent=None) -> None:
        super().__init__(orientation, parent)
        self.setSectionsClickable(True)

    def _visible_state(self):
        model = self.model()
        if model is None or model.rowCount() == 0:
            return Qt.Unchecked
        checked = 0
        for row in range(model.rowCount()):
            if model.index(row, 0).data(Qt.CheckStateRole) == Qt.Checked:
                checked += 1
        if checked == 0:
            return Qt.Unchecked
        if checked == model.rowCount():
            return Qt.Checked
        return Qt.PartiallyChecked

    def toggle_visible(self) -> None:
        model = self.model()
        if model is None:
            return
        target = Qt.Unchecked if self._visible_state() == Qt.Checked else Qt.Checked
        source = getattr(model, "sourceModel", lambda: None)()
        mapper = getattr(model, "mapToSource", None)
        for row in range(model.rowCount()):
            proxy_index = model.index(row, 0)
            source_index = mapper(proxy_index) if mapper and source is not None else proxy_index
            target_model = source if source is not None else model
            target_model.setData(source_index, target, Qt.CheckStateRole)
        self.viewport().update()
        self.check_state_changed.emit(target)

    def paintSection(self, painter, rect, logical_index):  # noqa: N802 - Qt override
        super().paintSection(painter, rect, logical_index)
        if logical_index != 0:
            return
        option = QStyleOptionButton()
        option.state |= QStyle.State_Enabled
        state = self._visible_state()
        if state == Qt.Checked:
            option.state |= QStyle.State_On
        elif state == Qt.PartiallyChecked:
            option.state |= QStyle.State_NoChange
        else:
            option.state |= QStyle.State_Off
        indicator = self.style().subElementRect(QStyle.SE_CheckBoxIndicator, option, self)
        option.rect = QRect(
            rect.center().x() - indicator.width() // 2,
            rect.center().y() - indicator.height() // 2,
            indicator.width(),
            indicator.height(),
        )
        self.style().drawControl(QStyle.CE_CheckBox, option, painter, self)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton and self.logicalIndexAt(event.position().toPoint()) == 0:
            self.toggle_visible()
            event.accept()
            return
        super().mousePressEvent(event)
