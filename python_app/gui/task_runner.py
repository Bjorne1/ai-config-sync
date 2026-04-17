from typing import Callable

from PySide6.QtCore import QThread, Signal


class TaskThread(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, task: Callable[[], object]) -> None:
        super().__init__()
        self._task = task
        self.completed_successfully = False

    def run(self) -> None:  # noqa: D401
        try:
            result = self._task()
        except Exception as error:  # noqa: BLE001
            self.failed.emit(str(error))
            return
        self.completed_successfully = True
        self.succeeded.emit(result)
