from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

SPINNER_FRAMES = ("◐", "◓", "◑", "◒")


class BusyIndicatorDriver(QObject):
    frame_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__(QApplication.instance())
        self._frame = 0
        self._timer = QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    @property
    def frame(self) -> int:
        return self._frame

    def glyph(self) -> str:
        return SPINNER_FRAMES[self._frame % len(SPINNER_FRAMES)]

    def _advance(self) -> None:
        self._frame = (self._frame + 1) % len(SPINNER_FRAMES)
        self.frame_changed.emit(self._frame)


_busy_driver: BusyIndicatorDriver | None = None


def busy_indicator_driver() -> BusyIndicatorDriver:
    global _busy_driver
    if _busy_driver is None:
        _busy_driver = BusyIndicatorDriver()
    return _busy_driver
