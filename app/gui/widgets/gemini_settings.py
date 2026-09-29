from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ai.gemini_agent import GEMINI_MODELS


class GeminiSettings(QWidget):
    save_requested = Signal(object, str)
    test_requested = Signal()
    clear_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        card = QFrame()
        card.setObjectName("Panel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Konfigurasi API Gemini")
        title.setObjectName("Heading")
        layout.addWidget(title)

        info = QLabel(
            "Tempel 1 sampai 100 API key Gemini. Bisa satu per baris atau dipisahkan koma. "
            "Setelah disimpan, kolom akan dikosongkan agar key tidak terus terlihat di layar."
        )
        info.setObjectName("Muted")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.keys = QTextEdit()
        self.keys.setPlaceholderText("AIza...\nAIza...\nAIza...")
        self.keys.setFixedHeight(118)
        layout.addWidget(self.keys)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model utama"))
        self.model = QComboBox()
        self.model.addItems(list(GEMINI_MODELS))
        model_row.addWidget(self.model, 1)
        layout.addLayout(model_row)

        buttons = QHBoxLayout()
        self.save = QPushButton("Simpan API")
        self.save.setObjectName("Primary")
        self.test = QPushButton("Tes API")
        self.clear = QPushButton("Hapus API")
        buttons.addWidget(self.save)
        buttons.addWidget(self.test)
        buttons.addWidget(self.clear)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.status = QLabel("Belum ada API key pada sesi ini.")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        root.addWidget(card)

        model_card = QFrame()
        model_card.setObjectName("Panel")
        model_layout = QVBoxLayout(model_card)
        model_layout.setContentsMargins(18, 16, 18, 16)
        heading = QLabel("Urutan fallback model")
        heading.setObjectName("Heading")
        model_layout.addWidget(heading)
        self.fallback = QLabel()
        self.fallback.setObjectName("Muted")
        self.fallback.setWordWrap(True)
        model_layout.addWidget(self.fallback)
        root.addWidget(model_card)
        root.addStretch(1)

        self.save.clicked.connect(self._save)
        self.test.clicked.connect(self.test_requested.emit)
        self.clear.clicked.connect(self._clear)
        self.model.currentTextChanged.connect(self._refresh_fallback)
        self._refresh_fallback()

    @staticmethod
    def _normalize(text: str) -> list[str]:
        values = text.replace(";", "\n").replace(",", "\n").splitlines()
        clean: list[str] = []
        for value in values:
            key = value.strip()
            if key and key not in clean:
                clean.append(key)
        return clean[:100]

    def _save(self) -> None:
        keys = self._normalize(self.keys.toPlainText())
        if not keys:
            self.status.setText("Masukkan minimal satu API key sebelum menekan Simpan API.")
            return
        self.save_requested.emit(keys, self.model.currentText())
        self.keys.clear()

    def _clear(self) -> None:
        self.keys.clear()
        self.clear_requested.emit()

    def _refresh_fallback(self) -> None:
        first = self.model.currentText()
        order = [first] + [item for item in GEMINI_MODELS if item != first]
        self.fallback.setText(" → ".join(order))

    def set_config(self, count: int, model: str) -> None:
        if model in GEMINI_MODELS:
            old = self.model.blockSignals(True)
            self.model.setCurrentText(model)
            self.model.blockSignals(old)
            self._refresh_fallback()
        if count:
            self.status.setText(f"Siap: {count} API key aktif pada sesi ini. Model utama: {model}.")
        else:
            self.status.setText("Belum ada API key pada sesi ini.")

    def set_test_result(self, ok: bool, message: str) -> None:
        prefix = "Berhasil" if ok else "Gagal"
        self.status.setText(f"{prefix}: {message}")
