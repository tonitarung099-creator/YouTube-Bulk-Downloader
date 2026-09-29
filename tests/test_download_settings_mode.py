from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.gui.widgets.panels import DownloadSettings
from app.models.commands import DownloadIntent


_APP = QApplication.instance() or QApplication([])


def test_selecting_audio_format_activates_audio_mode() -> None:
    widget = DownloadSettings()
    events: list[dict] = []
    widget.changed.connect(events.append)

    idx = widget.audio.findText("Opus")
    widget.audio.setCurrentIndex(idx)
    widget.audio.activated.emit(idx)

    assert events
    assert events[-1]["mode"] == "audio"
    assert events[-1]["quality"] == "best"
    assert events[-1]["audio_format"] == "opus"
    assert widget.qgroup.checkedButton().property("value") == "audio"
    assert "Audio" in widget.mode_status.text()


def test_selecting_mp4_switches_back_to_video_even_when_mp4_was_already_selected() -> None:
    widget = DownloadSettings()
    events: list[dict] = []
    widget.changed.connect(events.append)

    audio_idx = widget.audio.findText("MP3")
    widget.audio.setCurrentIndex(audio_idx)
    widget.audio.activated.emit(audio_idx)
    assert events[-1]["mode"] == "audio"

    mp4_idx = widget.video.findText("MP4")
    widget.video.setCurrentIndex(mp4_idx)
    widget.video.activated.emit(mp4_idx)

    assert events[-1]["mode"] == "video"
    assert events[-1]["video_format"] == "mp4"
    assert events[-1]["quality"] == "1080p"
    assert widget.qgroup.checkedButton().property("value") == "1080p"
    assert "Video" in widget.mode_status.text()


def test_video_quality_button_also_exits_audio_mode() -> None:
    widget = DownloadSettings()
    events: list[dict] = []
    widget.changed.connect(events.append)

    widget._quality_buttons["audio"].click()
    assert events[-1]["mode"] == "audio"

    widget._quality_buttons["720p"].click()
    assert events[-1]["mode"] == "video"
    assert events[-1]["quality"] == "720p"


def test_loading_audio_intent_then_choosing_mp4_is_not_overwritten() -> None:
    widget = DownloadSettings()
    events: list[dict] = []
    widget.changed.connect(events.append)
    widget.load_intent(
        DownloadIntent(
            mode="audio",
            quality="best",
            video_format="mp4",
            audio_format="mp3",
        )
    )

    assert widget.qgroup.checkedButton().property("value") == "audio"
    assert events == []

    mp4_idx = widget.video.findText("MP4")
    widget.video.activated.emit(mp4_idx)

    assert events[-1]["mode"] == "video"
    assert events[-1]["video_format"] == "mp4"
