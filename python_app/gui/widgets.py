from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .theme import STATE_COLORS, create_app_font, create_mono_font


class CardFrame(QFrame):
    def __init__(self, title: str = "", detail: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        self._header = QLabel(title)
        self._header.setObjectName("sectionTitle")
        self._detail = QLabel(detail)
        self._detail.setObjectName("muted")
        self._detail.setWordWrap(True)
        if title:
            layout.addWidget(self._header)
        if detail:
            layout.addWidget(self._detail)
        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(12)
        layout.addLayout(self.body_layout)


class MetricCard(QFrame):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        self.label = QLabel(label)
        self.label.setObjectName("eyebrow")
        self.value = QLabel("--")
        self.value.setFont(create_mono_font(22))
        self.note = QLabel("")
        self.note.setObjectName("muted")
        self.note.setWordWrap(True)
        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addWidget(self.note)

    def set_value(self, value: str, note: str) -> None:
        self.value.setText(value)
        self.note.setText(note)


class BadgeLabel(QLabel):
    def __init__(self, text: str, state: str = "idle", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(create_mono_font(9))
        self.set_state(state)

    def set_state(self, state: str) -> None:
        fg, bg = STATE_COLORS.get(state, STATE_COLORS["idle"])
        self.setStyleSheet(
            f"border: 1px solid {fg}; border-radius: 10px; padding: 4px 8px; color: {fg}; background: {bg};"
        )


class NavButton(QPushButton):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.setObjectName("navButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


class ActionButton(QPushButton):
    def __init__(self, label: str, variant: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.setObjectName(f"{variant}Button")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._base_label = label
        self._variant = variant

    def set_busy(self, busy: bool) -> None:
        self.setDisabled(busy)
        self.setText("处理中..." if busy else self._base_label)


class HeaderBlock(QWidget):
    def __init__(self, eyebrow: str, title: str, detail: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        eyebrow_label = QLabel(eyebrow)
        eyebrow_label.setObjectName("eyebrow")
        title_label = QLabel(title)
        title_label.setObjectName("title")
        detail_label = QLabel(detail)
        detail_label.setObjectName("muted")
        detail_label.setWordWrap(True)
        layout.addWidget(eyebrow_label)
        layout.addWidget(title_label)
        layout.addWidget(detail_label)


class ToolTargetGrid(CardFrame):
    def __init__(self, title: str, detail: str, tool_ids: tuple[str, ...], parent: QWidget | None = None) -> None:
        super().__init__(title, detail, parent)
        self._tool_ids = tool_ids
        self._inputs: dict[str, QLabel] = {}
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(10)
        self.body_layout.addLayout(self.grid)

    def add_row(self, tool_id: str, editor: QWidget) -> None:
        row = len(self._inputs)
        label = QLabel(tool_id.upper())
        label.setObjectName("eyebrow")
        self.grid.addWidget(label, row, 0)
        self.grid.addWidget(editor, row, 1)
        self._inputs[tool_id] = label
