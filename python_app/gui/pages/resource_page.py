from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.tool_definitions import TOOL_IDS
from ..dashboard import entry_summary, serialize
from ..widgets import ActionButton, CardFrame, HeaderBlock, configure_table

TABLE_HEADERS = ("选中", "名称", "类型", "摘要", "路径", "状态", "Claude", "Codex", "Gemini", "Antigravity")


class ResourcePage(QWidget):
    rescan_requested = Signal(str)
    save_requested = Signal(str, object)
    sync_requested = Signal(str, object)

    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.rows: list[dict[str, object]] = []
        self.selected_names: set[str] = set()
        self.assignments: dict[str, list[str]] = {}
        self._initial_assignments: dict[str, list[str]] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        title = "Skills" if self.kind == "skills" else "Commands"
        layout.addWidget(
            HeaderBlock(
                f"0{'2' if self.kind == 'skills' else '3'} / {title}",
                title,
                "资源分配草稿只留在界面层，保存后才写回配置。",
            )
        )
        layout.addWidget(self._build_toolbar_card())
        layout.addWidget(self._build_table_card(title), 1)

    def _build_toolbar_card(self) -> QWidget:
        card = CardFrame("筛选与动作", "搜索后可保存分配，也可以只同步当前勾选项。")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"搜索 {self.kind} 名称或路径")
        self.search.textChanged.connect(self._rebuild_table)
        self.rescan_button = ActionButton("重扫源目录", "secondary")
        self.save_button = ActionButton("保存分配", "primary")
        self.sync_button = ActionButton("同步勾选项", "secondary")
        self.rescan_button.clicked.connect(lambda: self.rescan_requested.emit(self.kind))
        self.save_button.clicked.connect(self._emit_save)
        self.sync_button.clicked.connect(self._emit_sync)
        grid.addWidget(self.search, 0, 0, 1, 2)
        grid.addWidget(self.rescan_button, 0, 2)
        grid.addWidget(self.save_button, 0, 3)
        grid.addWidget(self.sync_button, 0, 4)
        self.meta = QLabel("0 条记录")
        self.meta.setObjectName("muted")
        grid.addWidget(self.meta, 1, 0, 1, 5)
        card.body_layout.addLayout(grid)
        return card

    def _build_table_card(self, title: str) -> QWidget:
        card = CardFrame(f"{title} 清单", "按状态、路径和工具分配检查当前资源。")
        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        configure_table(self.table, stretch_columns=(3, 4, 5))
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setColumnWidth(0, 56)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 72)
        for column in range(6, len(TABLE_HEADERS)):
            self.table.setColumnWidth(column, 72)
        card.body_layout.addWidget(self.table)
        return card

    def _filtered_rows(self) -> list[dict[str, object]]:
        query = self.search.text().strip().lower()
        if not query:
            return self.rows
        return [row for row in self.rows if query in row["name"].lower() or query in row["path"].lower()]

    def _emit_save(self) -> None:
        self.save_requested.emit(self.kind, self.get_assignments())

    def _emit_sync(self) -> None:
        self.sync_requested.emit(self.kind, self.get_selected_names())

    def set_rows(self, rows: list[dict[str, object]]) -> None:
        self.rows = deepcopy(rows)
        self.assignments = {row["name"]: list(row["configuredTools"]) for row in rows if row["configuredTools"]}
        self._initial_assignments = deepcopy(self.assignments)
        self.selected_names &= {row["name"] for row in rows}
        self._rebuild_table()

    def get_assignments(self) -> dict[str, list[str]]:
        return {name: tools for name, tools in self.assignments.items() if tools}

    def get_selected_names(self) -> list[str]:
        visible = {row["name"] for row in self._filtered_rows()}
        return sorted(self.selected_names & visible)

    def set_busy(self, rescan_busy: bool, save_busy: bool, sync_busy: bool) -> None:
        self.rescan_button.set_busy(rescan_busy)
        self.save_button.set_busy(save_busy)
        self.sync_button.set_busy(sync_busy)

    def _rebuild_table(self) -> None:
        rows = self._filtered_rows()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self._fill_row(row_index, row)
        dirty = serialize(self.assignments) != serialize(self._initial_assignments)
        self.meta.setText(f"{len(self.rows)} 条记录 · {'存在未保存分配' if dirty else '分配已同步'}")

    def _fill_row(self, row_index: int, row: dict[str, object]) -> None:
        self._set_select_cell(row_index, row["name"])
        type_label = "目录" if row["isDirectory"] else "文件"
        path_text = row["path"] or "源路径不可用"
        status_text = entry_summary(row["entries"])
        values = [row["name"], type_label, row["summaryMessage"], path_text, status_text]
        for column, value in enumerate(values, start=1):
            item = QTableWidgetItem(value)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_index, column, item)
        for offset, tool_id in enumerate(TOOL_IDS, start=6):
            self.table.setCellWidget(row_index, offset, self._tool_checkbox(row["name"], tool_id))

    def _set_select_cell(self, row_index: int, name: str) -> None:
        checkbox = QCheckBox()
        checkbox.setChecked(name in self.selected_names)
        checkbox.stateChanged.connect(lambda state, item=name: self._toggle_selected(item, state))
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(checkbox)
        self.table.setCellWidget(row_index, 0, wrapper)

    def _tool_checkbox(self, name: str, tool_id: str) -> QWidget:
        checkbox = QCheckBox()
        checkbox.setChecked(tool_id in self.assignments.get(name, []))
        checkbox.stateChanged.connect(lambda state, item=name, tool=tool_id: self._toggle_tool(item, tool, state))
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(checkbox)
        return wrapper

    def _toggle_selected(self, name: str, state: int) -> None:
        if state == Qt.CheckState.Checked.value:
            self.selected_names.add(name)
            return
        self.selected_names.discard(name)

    def _toggle_tool(self, name: str, tool_id: str, state: int) -> None:
        tools = list(self.assignments.get(name, []))
        checked = state == Qt.CheckState.Checked.value
        if checked and tool_id not in tools:
            tools.append(tool_id)
        if not checked and tool_id in tools:
            tools.remove(tool_id)
        ordered = [tool for tool in TOOL_IDS if tool in tools]
        if ordered:
            self.assignments[name] = ordered
        else:
            self.assignments.pop(name, None)
        self._rebuild_table()
