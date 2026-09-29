from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel


class VideoFilterProxyModel(QSortFilterProxyModel):
    """Gabungkan pencarian judul dan filter jenis tanpa mengubah selection ID."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._search = ""
        self._kind: str | None = None
        self.setDynamicSortFilter(True)

    def set_search(self, text: str) -> None:
        value = text.strip().casefold()
        if value != self._search:
            self.beginFilterChange()
            self._search = value
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_kind(self, kind: str | None) -> None:
        value = kind.strip().casefold() if kind else None
        if value != self._kind:
            self.beginFilterChange()
            self._kind = value
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:  # noqa: N802 - Qt API
        model = self.sourceModel()
        title = str(model.index(source_row, 3, source_parent).data() or "").casefold()
        kind = str(model.index(source_row, 5, source_parent).data() or "").casefold()
        return (not self._search or self._search in title) and (not self._kind or kind == self._kind)
