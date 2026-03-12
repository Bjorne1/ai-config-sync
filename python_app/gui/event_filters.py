from PySide6.QtCore import QEvent, QObject


class WheelBlocker(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._enabled = False

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self._enabled and event.type() == QEvent.Type.Wheel:
            return True
        return super().eventFilter(watched, event)
