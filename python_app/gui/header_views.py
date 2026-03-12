from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHeaderView, QStyle, QStyleOptionButton, QWidget

from .theme import BORDER, SURFACE_ALT, TEXT_MUTED


class GroupedHeaderView(QHeaderView):
    checkbox_state_changed = Signal(int, int)

    def __init__(
        self,
        groups: tuple[tuple[str, tuple[int, ...]], ...],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._groups = groups
        self._grouped_columns = {column for _label, columns in groups for column in columns}
        self._top_height = 22
        self._single_height = 30
        self._checkbox_sections: set[int] = set()
        self._checkbox_states: dict[int, Qt.CheckState] = {}
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._apply_header_height()

    def enable_checkbox(self, logical_index: int) -> None:
        self._checkbox_sections.add(logical_index)
        self._checkbox_states.setdefault(logical_index, Qt.CheckState.Unchecked)
        self.viewport().update()

    def set_checkbox_state(self, logical_index: int, state: Qt.CheckState) -> None:
        if logical_index not in self._checkbox_sections:
            return
        self._checkbox_states[logical_index] = state
        self.viewport().update()

    def checkbox_state(self, logical_index: int) -> Qt.CheckState:
        return self._checkbox_states.get(logical_index, Qt.CheckState.Unchecked)

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(max(hint.height(), self._header_height()))
        return hint

    def mousePressEvent(self, event) -> None:
        logical_index = self.logicalIndexAt(event.position().toPoint())
        if logical_index in self._checkbox_sections:
            state = self.checkbox_state(logical_index)
            next_state = Qt.CheckState.Unchecked if state == Qt.CheckState.Checked else Qt.CheckState.Checked
            self.set_checkbox_state(logical_index, next_state)
            self.checkbox_state_changed.emit(logical_index, next_state.value)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        self._apply_header_height()
        show_detail_row = self._show_group_detail_row()
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        for logical_index in range(self.count()):
            if self.isSectionHidden(logical_index):
                continue
            rect = self._section_rect(logical_index)
            if not rect.isValid() or not rect.intersects(event.rect()):
                continue
            if logical_index in self._checkbox_sections:
                self._draw_checkbox_cell(painter, rect, self.checkbox_state(logical_index))
                continue
            label = self._header_label(logical_index)
            if logical_index in self._grouped_columns:
                if show_detail_row:
                    self._draw_cell(painter, rect.adjusted(0, self._top_height, 0, 0), label)
                continue
            self._draw_cell(painter, rect, label)
        for group_label, columns in self._groups:
            rect = self._group_rect(columns, show_detail_row)
            if rect and rect.intersects(event.rect()):
                self._draw_cell(painter, rect, group_label, center=True)

    def _header_height(self) -> int:
        if self._show_group_detail_row():
            return self._top_height + self._single_height
        return self._single_height

    def _apply_header_height(self) -> None:
        height = self._header_height()
        if self.minimumHeight() == height and self.maximumHeight() == height:
            return
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.updateGeometry()

    def _show_group_detail_row(self) -> bool:
        if not self._groups:
            return False
        return any(self._header_label(column).strip() for column in self._grouped_columns)

    def _header_label(self, logical_index: int) -> str:
        if not self.model():
            return ""
        value = self.model().headerData(logical_index, self.orientation(), Qt.ItemDataRole.DisplayRole)
        return str(value or "")

    def _section_rect(self, logical_index: int):
        return self.viewport().rect().adjusted(
            self.sectionViewportPosition(logical_index),
            0,
            self.sectionViewportPosition(logical_index) + self.sectionSize(logical_index) - self.viewport().width(),
            0,
        )

    def _group_rect(self, columns: tuple[int, ...], show_detail_row: bool):
        visible = [column for column in columns if not self.isSectionHidden(column)]
        if not visible:
            return None
        left = self.sectionViewportPosition(visible[0])
        right = self.sectionViewportPosition(visible[-1]) + self.sectionSize(visible[-1])
        bottom = self._top_height - self.height() if show_detail_row else 0
        return self.viewport().rect().adjusted(left, 0, right - self.viewport().width(), bottom)

    def _draw_cell(self, painter: QPainter, rect, text: str, center: bool = False) -> None:
        painter.save()
        painter.fillRect(rect, QColor(SURFACE_ALT))
        painter.setPen(QPen(QColor(BORDER)))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())
        painter.setPen(QColor(TEXT_MUTED))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        alignment = Qt.AlignmentFlag.AlignCenter if center else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        painter.drawText(rect.adjusted(8, 0, -8, 0), alignment, text)
        painter.restore()

    def _draw_checkbox_cell(self, painter: QPainter, rect, state: Qt.CheckState) -> None:
        painter.save()
        painter.fillRect(rect, QColor(SURFACE_ALT))
        painter.setPen(QPen(QColor(BORDER)))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())
        option = QStyleOptionButton()
        option.state |= QStyle.StateFlag.State_Enabled
        if state == Qt.CheckState.Checked:
            option.state |= QStyle.StateFlag.State_On
        elif state == Qt.CheckState.PartiallyChecked:
            option.state |= QStyle.StateFlag.State_NoChange
        else:
            option.state |= QStyle.StateFlag.State_Off
        size = 16
        option.rect = rect.adjusted(
            (rect.width() - size) // 2,
            (rect.height() - size) // 2,
            -((rect.width() - size) // 2),
            -((rect.height() - size) // 2),
        )
        self.style().drawControl(QStyle.ControlElement.CE_CheckBox, option, painter, self)
        painter.restore()

