from PySide6.QtCore import Qt
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

from .header_views import GroupedHeaderView
from .theme import STATE_COLORS, create_mono_font


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
