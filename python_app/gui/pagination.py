from collections.abc import Sequence
from typing import TypeVar

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..core.tool_definitions import TOOL_IDS
from .theme import (
    ACCENT,
    ACCENT_SOFT,
    BORDER,
    INFO,
    SUCCESS,
    TEXT_MUTED,
)

from .widgets import ActionButton

T = TypeVar("T")

MAX_DISPLAY_COUNT = 99

ANTIGRAVITY_FG = "#6d28d9"
ANTIGRAVITY_BG = "#ede9fe"
TOOL_PILL_COLORS: dict[str, tuple[str, str]] = {
    "claude": (ACCENT, ACCENT_SOFT),
    "codex": (SUCCESS, "#dcfce7"),
    "gemini": (INFO, "#dbeafe"),
    "antigravity": (ANTIGRAVITY_FG, ANTIGRAVITY_BG),
}
TOOL_PILL_LABELS: dict[str, str] = {
    "claude": "Claude",
    "codex": "Codex",
    "gemini": "Gemini",
    "antigravity": "Antigravity",
}


def paginate(rows: Sequence[T], page_index: int, page_size: int) -> tuple[list[T], int, int, int]:
    total = len(rows)
    if total == 0:
        return [], 0, 0, 0
    page_count = (total + page_size - 1) // page_size
    page_index = max(0, min(page_index, page_count - 1))
    start = page_index * page_size
    return list(rows[start : start + page_size]), page_index, page_count, total


class StatPill(QLabel):
    def __init__(self, text: str, fg: str, bg: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._fg = fg
        self._bg = bg
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"border: 1px solid {self._fg}; border-radius: 12px; padding: 3px 10px; color: {self._fg}; background: {self._bg};"
        )


class StatTag(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("muted")
        self.setStyleSheet(
            f"border: 1px solid {BORDER}; border-radius: 12px; padding: 3px 10px; color: {TEXT_MUTED}; background: transparent;"
        )


class ToolStatsRow(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._tag = StatTag(label)
        layout.addWidget(self._tag)
        self._pills: dict[str, StatPill] = {}
        for tool_id in TOOL_IDS:
            fg, bg = TOOL_PILL_COLORS.get(tool_id, (TEXT_MUTED, "transparent"))
            pill = StatPill(self._pill_text(tool_id, 0), fg, bg)
            self._pills[tool_id] = pill
            layout.addWidget(pill)
        layout.addStretch(1)

    def set_counts(self, counts: dict[str, int]) -> None:
        for tool_id in TOOL_IDS:
            value = int(counts.get(tool_id, 0))
            pill = self._pills.get(tool_id)
            if pill is not None:
                pill.setText(self._pill_text(tool_id, value))

    def set_pill_widths(self, widths: dict[str, int]) -> None:
        for tool_id, pill in self._pills.items():
            width = widths.get(tool_id)
            if width is not None:
                pill.setFixedWidth(width)

    def required_width(self, max_value: int) -> int:
        previous = {tool_id: pill.text() for tool_id, pill in self._pills.items()}
        try:
            for tool_id, pill in self._pills.items():
                pill.setText(self._pill_text(tool_id, max_value))
            return self.sizeHint().width()
        finally:
            for tool_id, pill in self._pills.items():
                pill.setText(previous.get(tool_id, self._pill_text(tool_id, 0)))

    def required_pill_widths(self, max_value: int) -> dict[str, int]:
        previous = {tool_id: pill.text() for tool_id, pill in self._pills.items()}
        try:
            widths: dict[str, int] = {}
            for tool_id, pill in self._pills.items():
                pill.setText(self._pill_text(tool_id, max_value))
                widths[tool_id] = pill.sizeHint().width()
            return widths
        finally:
            for tool_id, pill in self._pills.items():
                pill.setText(previous.get(tool_id, self._pill_text(tool_id, 0)))

    def _pill_text(self, tool_id: str, value: int) -> str:
        label = TOOL_PILL_LABELS.get(tool_id, tool_id)
        return f"{label}: {value}"


class Pager(QWidget):
    page_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_index = 0
        self._page_count = 0
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self._stats = QWidget()
        stats_layout = QVBoxLayout(self._stats)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(4)
        self._win_stats = ToolStatsRow("WIN 已安装")
        self._wsl_stats = ToolStatsRow("WSL 已安装")
        stats_layout.addWidget(self._win_stats)
        stats_layout.addWidget(self._wsl_stats)
        self._fix_stats_width()
        self.prev_button = ActionButton("上一页", "secondary")
        self.next_button = ActionButton("下一页", "secondary")
        self.label = QLabel("")
        self.label.setObjectName("muted")
        self.prev_button.clicked.connect(self._request_prev)
        self.next_button.clicked.connect(self._request_next)
        layout.addWidget(self._stats)
        layout.addStretch(1)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.label)
        self.set_state(0, 0, 0)
        self.set_stats({"windows": {}, "wsl": {}})

    def _fix_stats_width(self) -> None:
        win_widths = self._win_stats.required_pill_widths(MAX_DISPLAY_COUNT)
        wsl_widths = self._wsl_stats.required_pill_widths(MAX_DISPLAY_COUNT)
        merged_widths = {tool_id: max(win_widths.get(tool_id, 0), wsl_widths.get(tool_id, 0)) for tool_id in TOOL_IDS}
        self._win_stats.set_pill_widths(merged_widths)
        self._wsl_stats.set_pill_widths(merged_widths)

        fixed_width = max(
            self._win_stats.required_width(MAX_DISPLAY_COUNT),
            self._wsl_stats.required_width(MAX_DISPLAY_COUNT),
        )
        self._stats.setFixedWidth(fixed_width)

    def set_state(self, page_index: int, page_count: int, total: int) -> None:
        self._page_index = page_index
        self._page_count = page_count
        self.prev_button.setEnabled(page_index > 0)
        self.next_button.setEnabled(page_count > 0 and page_index + 1 < page_count)
        if page_count == 0:
            self.label.setText("共 0 条")
            return
        self.label.setText(f"第 {page_index + 1} / {page_count} 页 · 共 {total} 条")

    def set_stats(self, stats: dict[str, dict[str, int]]) -> None:
        self._win_stats.set_counts(stats.get("windows", {}))
        self._wsl_stats.set_counts(stats.get("wsl", {}))

    def _request_prev(self) -> None:
        if self._page_index <= 0:
            return
        self.page_requested.emit(self._page_index - 1)

    def _request_next(self) -> None:
        if self._page_count == 0 or self._page_index + 1 >= self._page_count:
            return
        self.page_requested.emit(self._page_index + 1)
