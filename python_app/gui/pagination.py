from collections.abc import Sequence
from typing import TypeVar

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from .widgets import ActionButton

T = TypeVar("T")


def paginate(rows: Sequence[T], page_index: int, page_size: int) -> tuple[list[T], int, int, int]:
    total = len(rows)
    if total == 0:
        return [], 0, 0, 0
    page_count = (total + page_size - 1) // page_size
    page_index = max(0, min(page_index, page_count - 1))
    start = page_index * page_size
    return list(rows[start : start + page_size]), page_index, page_count, total


class Pager(QWidget):
    page_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_index = 0
        self._page_count = 0
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.prev_button = ActionButton("上一页", "secondary")
        self.next_button = ActionButton("下一页", "secondary")
        self.label = QLabel("")
        self.label.setObjectName("muted")
        self.prev_button.clicked.connect(self._request_prev)
        self.next_button.clicked.connect(self._request_next)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.next_button)
        layout.addStretch(1)
        layout.addWidget(self.label)
        self.set_state(0, 0, 0)

    def set_state(self, page_index: int, page_count: int, total: int) -> None:
        self._page_index = page_index
        self._page_count = page_count
        self.prev_button.setEnabled(page_index > 0)
        self.next_button.setEnabled(page_count > 0 and page_index + 1 < page_count)
        if page_count == 0:
            self.label.setText("共 0 条")
            return
        self.label.setText(f"第 {page_index + 1} / {page_count} 页 · 共 {total} 条")

    def _request_prev(self) -> None:
        if self._page_index <= 0:
            return
        self.page_requested.emit(self._page_index - 1)

    def _request_next(self) -> None:
        if self._page_count == 0 or self._page_index + 1 >= self._page_count:
            return
        self.page_requested.emit(self._page_index + 1)
