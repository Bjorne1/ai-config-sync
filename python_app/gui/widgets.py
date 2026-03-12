from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableView,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .theme import BORDER, STATE_COLORS, SURFACE_ALT, TEXT_MUTED, create_mono_font


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
        self.setMinimumHeight(152)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        self.label = QLabel(label)
        self.label.setObjectName("eyebrow")
        self.value = QLabel("--")
        self.value.setFont(create_mono_font(24))
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


class GroupedHeaderView(QHeaderView):
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
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._apply_header_height()

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(max(hint.height(), self._header_height()))
        return hint

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


class FrozenRightTableWidget(QTableWidget):
    def __init__(
        self,
        rows: int,
        columns: int,
        frozen_columns: tuple[int, ...],
        frozen_groups: tuple[tuple[str, tuple[int, ...]], ...] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(rows, columns, parent)
        self._frozen_columns = tuple(sorted(frozen_columns))
        self.setHorizontalHeader(GroupedHeaderView((), self))
        self._frozen_view = QTableView(self)
        self._frozen_view.setModel(self.model())
        self._frozen_view.setSelectionModel(self.selectionModel())
        self._frozen_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._frozen_view.setFrameShape(QFrame.Shape.NoFrame)
        self._frozen_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._frozen_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._frozen_view.setHorizontalHeader(GroupedHeaderView(frozen_groups, self._frozen_view))
        self.viewport().stackUnder(self._frozen_view)
        self._apply_frozen_columns()
        self.horizontalHeader().sectionResized.connect(self._handle_section_resized)
        self.verticalHeader().sectionResized.connect(self._handle_row_resized)
        self.verticalScrollBar().valueChanged.connect(self._frozen_view.verticalScrollBar().setValue)
        self._frozen_view.verticalScrollBar().valueChanged.connect(self.verticalScrollBar().setValue)
        self._sync_row_heights()
        self._update_frozen_geometry()
        self._frozen_view.show()

    def frozen_view(self) -> QTableView:
        return self._frozen_view

    def sync_frozen_view(self) -> None:
        self._apply_frozen_columns()
        self._sync_row_heights()
        self._update_frozen_geometry()
        self.viewport().update()
        self._frozen_view.viewport().update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_frozen_geometry()

    def updateGeometries(self) -> None:
        super().updateGeometries()
        self.setViewportMargins(0, self.horizontalHeader().height(), self._frozen_width(), 0)
        self._update_frozen_geometry()

    def _frozen_width(self) -> int:
        return sum(self._frozen_view.columnWidth(column) for column in self._frozen_columns)

    def _apply_frozen_columns(self) -> None:
        frozen_set = set(self._frozen_columns)
        for column in range(self.columnCount()):
            self.setColumnHidden(column, column in frozen_set)
            self._frozen_view.setColumnHidden(column, column not in frozen_set)

    def _sync_row_heights(self) -> None:
        for row in range(self.rowCount()):
            self._frozen_view.setRowHeight(row, self.rowHeight(row))

    def _update_frozen_geometry(self) -> None:
        frozen_width = self._frozen_width()
        viewport = self.viewport().geometry()
        self._frozen_view.setGeometry(
            viewport.x() + viewport.width(),
            self.frameWidth(),
            frozen_width,
            self.viewport().height() + self.horizontalHeader().height(),
        )

    def _handle_section_resized(self, logical_index: int, _old_size: int, new_size: int) -> None:
        if logical_index in self._frozen_columns:
            self._frozen_view.setColumnWidth(logical_index, new_size)
            self._update_frozen_geometry()

    def _handle_row_resized(self, logical_index: int, _old_size: int, new_size: int) -> None:
        self._frozen_view.setRowHeight(logical_index, new_size)


def layout_container(layout: QLayout, max_vertical: bool = True) -> QWidget:
    container = QWidget()
    container.setLayout(layout)
    vertical_policy = QSizePolicy.Policy.Maximum if max_vertical else QSizePolicy.Policy.Expanding
    container.setSizePolicy(QSizePolicy.Policy.Expanding, vertical_policy)
    return container


def configure_table(table: QTableView, stretch_columns: tuple[int, ...] = ()) -> None:
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setWordWrap(False)
    table.setShowGrid(False)
    if isinstance(table, QTableWidget):
        table.setCornerButtonEnabled(False)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(42)
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    column_count = table.model().columnCount() if table.model() else 0
    for index in range(column_count):
        mode = QHeaderView.ResizeMode.Stretch if index in stretch_columns else QHeaderView.ResizeMode.ResizeToContents
        header.setSectionResizeMode(index, mode)
