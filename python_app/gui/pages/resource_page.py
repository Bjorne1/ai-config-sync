from copy import deepcopy
from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from ...core.tool_definitions import TOOL_IDS
from ..event_filters import WheelBlocker
from ..logo_matrix import (
    LOGO_ACTIVE_ROLE,
    LOGO_STATE_ROLE,
    LOGO_TOOL_ROLE,
    ACTION_COLUMN,
    MATRIX_COLUMNS,
    MATRIX_END_COLUMN,
    MATRIX_GROUPS,
    TABLE_HEADERS,
    ToolLogoDelegate,
    find_matrix_entry,
    is_action_cell,
    is_matrix_cell,
    matrix_column,
    matrix_tooltip,
)
from ..pagination import Pager, paginate
from .resource_selection import PageSelection
from ..widgets import ActionButton, CardFrame, FrozenRightTableWidget, configure_table
RESOURCE_ROWS_PER_PAGE = 10
NAME_CELL_PREVIEW_CHARS = 90
ROW_HEIGHT_DEFAULT = 42
ROW_HEIGHT_WITH_DESCRIPTION = 58
ENVIRONMENT_IDS = ("windows", "wsl")


def _truncate(text: str, limit: int) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}…"


def _build_name_tooltip(description: str, path: str) -> str:
    parts = [part for part in (description.strip(), path.strip()) if part]
    return "\n\n".join(parts)


def _build_name_cell(name: str, description: str, tooltip: str) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 2, 0, 2)
    layout.setSpacing(2)

    name_label = QLabel(name)
    name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    layout.addWidget(name_label)

    if description.strip():
        desc_label = QLabel(_truncate(description, NAME_CELL_PREVIEW_CHARS))
        desc_label.setObjectName("muted")
        desc_label.setWordWrap(False)
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(desc_label)

    container.setToolTip(tooltip or name)
    return container


class ResourcePage(QWidget):
    rescan_requested = Signal(str)
    sync_requested = Signal(str, object)
    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.rows: list[dict[str, object]] = []
        self.selected_names: set[str] = set()
        self.assignments: dict[str, dict[str, list[str]]] = {}
        self._updating_table = False
        self._page_selection: PageSelection | None = None
        self._page_index = 0
        self._page_size = RESOURCE_ROWS_PER_PAGE
        self._visible_rows: list[dict[str, object]] = []
        self._build_ui()
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        title = "Skills" if self.kind == "skills" else "Commands"
        layout.addWidget(self._build_toolbar_card())
        layout.addWidget(self._build_table_card(title), 1)
    def _build_toolbar_card(self) -> QWidget:
        card = CardFrame()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"搜索 {self.kind} 名称或路径")
        self.search.textChanged.connect(self._handle_filter_changed)
        self.rescan_button = ActionButton("重扫源目录", "secondary")
        self.sync_button = ActionButton("同步勾选项", "secondary")
        self.upgrade_button = ActionButton("升级所有", "secondary")
        self.remove_button = ActionButton("撤销勾选项", "danger")
        self.rescan_button.clicked.connect(lambda: self.rescan_requested.emit(self.kind))
        self.sync_button.clicked.connect(self._emit_sync)
        self.upgrade_button.clicked.connect(self._emit_upgrade_all)
        self.remove_button.clicked.connect(self._emit_remove)
        grid.addWidget(self.search, 0, 0, 1, 2)
        grid.addWidget(self.rescan_button, 0, 2)
        grid.addWidget(self.sync_button, 0, 3)
        grid.addWidget(self.upgrade_button, 0, 4)
        grid.addWidget(self.remove_button, 0, 5)
        self.meta = QLabel("0 条记录")
        self.meta.setObjectName("muted")
        grid.addWidget(self.meta, 1, 0, 1, 6)
        card.body_layout.addLayout(grid)
        return card
    def _build_table_card(self, title: str) -> QWidget:
        card = CardFrame(f"{title} 清单", "按状态、路径和工具分配检查当前资源。")
        self.table = FrozenRightTableWidget(0, len(TABLE_HEADERS), tuple(range(3, len(TABLE_HEADERS))), MATRIX_GROUPS)
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        configure_table(self.table, stretch_columns=(1,))
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        frozen_view = self.table.frozen_view()
        configure_table(frozen_view)
        self._table_wheel_blocker = WheelBlocker(self.table)
        self._table_wheel_blocker.set_enabled(True)
        self.table.viewport().installEventFilter(self._table_wheel_blocker)
        frozen_view.viewport().installEventFilter(self._table_wheel_blocker)
        header = self.table.horizontalHeader()
        fixed_columns = {0: 56, 2: 80}
        for column, width in fixed_columns.items():
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        matrix_header = frozen_view.horizontalHeader()
        for column in range(3, len(TABLE_HEADERS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            matrix_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, 78)
            frozen_view.setColumnWidth(column, 78)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        frozen_view.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._page_selection = PageSelection(self.table, self.selected_names, self._visible_names, self._update_meta)
        self._page_selection.configure_header_checkbox()
        for column, label in enumerate(TABLE_HEADERS):
            item = self.table.horizontalHeaderItem(column)
            if item:
                if column < 3:
                    item.setToolTip(label)
                elif column <= MATRIX_END_COLUMN:
                    item.setToolTip(MATRIX_COLUMNS[column - 3][3])
                else:
                    item.setToolTip("操作：仅在 copy 模式下，当源更新于目标时可执行“升级”。")
        self._logo_delegate = ToolLogoDelegate(self.table)
        for column in range(3, MATRIX_END_COLUMN + 1):
            self.table.setItemDelegateForColumn(column, self._logo_delegate)
            frozen_view.setItemDelegateForColumn(column, self._logo_delegate)
        self.table.clicked.connect(self._handle_matrix_clicked)
        frozen_view.clicked.connect(self._handle_matrix_clicked)
        self.table.sync_frozen_view()
        self.pager = Pager()
        self.pager.page_requested.connect(self._set_page)
        card.body_layout.addWidget(self.pager)
        card.body_layout.addWidget(self.table, 1)
        return card

    def _filtered_rows(self) -> list[dict[str, object]]:
        query = self.search.text().strip().lower()
        if not query:
            return self.rows
        return [row for row in self.rows if query in row["name"].lower() or query in row["path"].lower()]

    def _emit_sync(self) -> None:
        names = self.get_selected_names()
        assignments = self._build_bulk_assignments(names)
        self.sync_requested.emit(
            self.kind,
            {
                "action": "sync",
                "names": names,
                "assignments": assignments,
                "commitAssignments": assignments,
            },
        )

    def _emit_remove(self) -> None:
        names = self.get_selected_names()
        assignments = self._build_bulk_assignments(names)
        self.sync_requested.emit(
            self.kind,
            {
                "action": "remove",
                "names": names,
                "assignments": assignments,
                "commitRemove": True,
            },
        )

    def _emit_upgrade_all(self) -> None:
        names = self._upgradeable_names()
        assignments = self._build_upgrade_assignments(names)
        self.sync_requested.emit(
            self.kind,
            {
                "action": "upgrade",
                "names": names,
                "assignments": assignments,
            },
        )

    def set_rows(self, rows: list[dict[str, object]]) -> None:
        self.rows = deepcopy(rows)
        self.assignments = {
            row["name"]: deepcopy(row["effectiveTargets"])
            for row in rows
            if self._has_assignments(row["effectiveTargets"])
        }
        self.selected_names &= {row["name"] for row in rows}
        self._rebuild_table()

    def get_assignments(self) -> dict[str, dict[str, list[str]]]:
        return {name: targets for name, targets in self.assignments.items() if self._has_assignments(targets)}

    def get_selected_names(self) -> list[str]:
        visible = {row["name"] for row in self._filtered_rows()}
        return sorted(self.selected_names & visible)

    def set_busy(self, rescan_busy: bool, sync_busy: bool) -> None:
        self.rescan_button.set_busy(rescan_busy)
        self.sync_button.set_busy(sync_busy)
        self.upgrade_button.set_busy(sync_busy)
        self.remove_button.set_busy(sync_busy)

    def _handle_filter_changed(self) -> None:
        self._page_index = 0
        self._rebuild_table()

    def _set_page(self, index: int) -> None:
        self._page_index = index
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        rows = self._filtered_rows()
        self.pager.set_stats(self._count_installed(rows))
        self._visible_rows, self._page_index, page_count, total = paginate(rows, self._page_index, self._page_size)
        self._updating_table = True
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._visible_rows))
        for row_index, row in enumerate(self._visible_rows):
            self._fill_row(row_index, row)
        self.table.blockSignals(False)
        self._updating_table = False
        self.table.sync_frozen_view()
        if self._page_selection:
            self._page_selection.update_header_state()
        self._update_meta()
        self.pager.set_state(self._page_index, page_count, total)

    def _count_installed(self, rows: list[dict[str, object]]) -> dict[str, dict[str, int]]:
        tools = list(TOOL_IDS)
        stats = {env_id: {tool_id: 0 for tool_id in tools} for env_id in ENVIRONMENT_IDS}
        for row in rows:
            targets = row.get("effectiveTargets") or {}
            for env_id in ENVIRONMENT_IDS:
                for tool_id in targets.get(env_id, []) or []:
                    if tool_id in stats[env_id]:
                        stats[env_id][tool_id] += 1
        return stats

    def _update_meta(self) -> None:
        self.meta.setText(f"{len(self.rows)} 条记录 · 已勾选 {len(self.selected_names)} 项")

    def _fill_row(self, row_index: int, row: dict[str, object]) -> None:
        self._set_select_cell(row_index, row["name"])
        type_label = "目录" if row["isDirectory"] else "文件"
        self._set_name_cell(row_index, row)
        type_item = QTableWidgetItem(type_label)
        type_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        type_item.setToolTip(type_label)
        self.table.setItem(row_index, 2, type_item)
        for offset, (environment_id, tool_id, _label, _tooltip) in enumerate(MATRIX_COLUMNS):
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._apply_matrix_item_state(item, row, environment_id, tool_id)
            self.table.setItem(row_index, offset + 3, item)
        upgrade_item = QTableWidgetItem("升级" if self._is_upgradeable_row(row) else "")
        upgrade_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        upgrade_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        upgrade_item.setToolTip("点击升级：仅同步“目标缺失/源更新于目标”的条目，跳过覆盖风险项。")
        self.table.setItem(row_index, ACTION_COLUMN, upgrade_item)
        self._sync_row_height(row_index, row.get("description", ""))

    def _set_select_cell(self, row_index: int, name: str) -> None:
        checkbox = QCheckBox()
        checkbox.setChecked(name in self.selected_names)
        checkbox.stateChanged.connect(lambda state, item=name: self._toggle_selected(item, state))
        wrapper = QWidget()
        wrapper.setToolTip("勾选后参与“同步勾选项 / 撤销勾选项”")
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(checkbox)
        self.table.setCellWidget(row_index, 0, wrapper)

    def _set_name_cell(self, row_index: int, row: dict[str, object]) -> None:
        name = str(row.get("name", ""))
        description = str(row.get("description", ""))
        path = str(row.get("path", ""))
        tooltip = _build_name_tooltip(description, path)
        self.table.setCellWidget(row_index, 1, _build_name_cell(name, description, tooltip))

    def _sync_row_height(self, row_index: int, description: str) -> None:
        height = ROW_HEIGHT_WITH_DESCRIPTION if description.strip() else ROW_HEIGHT_DEFAULT
        self.table.setRowHeight(row_index, height)

    def _toggle_selected(self, name: str, state: int) -> None:
        if state == Qt.CheckState.Checked.value:
            self.selected_names.add(name)
        else:
            self.selected_names.discard(name)
        if self._page_selection:
            self._page_selection.update_header_state()
        self._update_meta()

    def _visible_names(self) -> list[str]:
        return [row["name"] for row in self._visible_rows]

    def _build_bulk_assignments(self, names: list[str]) -> dict[str, dict[str, list[str]]]:
        tools = list(TOOL_IDS)
        return {name: {"windows": tools, "wsl": tools} for name in names}

    def _is_upgradeable_row(self, row: dict[str, object]) -> bool:
        return any(entry.get("state") in {"missing", "outdated"} for entry in row.get("entries", []))

    def _upgradeable_names(self) -> list[str]:
        names: list[str] = []
        for row in self._filtered_rows():
            if not self._is_upgradeable_row(row):
                continue
            targets = self.assignments.get(row["name"], {})
            if self._has_assignments(targets):
                names.append(row["name"])
        return sorted(names)

    def _build_upgrade_assignments(self, names: list[str]) -> dict[str, dict[str, list[str]]]:
        return {name: deepcopy(self.assignments.get(name, {})) for name in names}

    def _toggle_tool(self, name: str, environment_id: str, tool_id: str, state: int) -> None:
        targets = deepcopy(self.assignments.get(name, {}))
        tools = list(targets.get(environment_id, []))
        checked = state == Qt.CheckState.Checked.value
        if checked and tool_id not in tools:
            tools.append(tool_id)
        if not checked and tool_id in tools:
            tools.remove(tool_id)
        ordered = [tool for tool in TOOL_IDS if tool in tools]
        if ordered:
            targets[environment_id] = ordered
        else:
            targets.pop(environment_id, None)
        if self._has_assignments(targets):
            self.assignments[name] = targets
        else:
            self.assignments.pop(name, None)
        self._update_meta()

    def _handle_matrix_clicked(self, index: QModelIndex) -> None:
        if self._updating_table:
            return
        if is_action_cell(index):
            self._handle_upgrade_clicked(index)
            return
        if not is_matrix_cell(index):
            return
        row = index.row()
        if row >= len(self._visible_rows):
            return
        resource = self._visible_rows[row]
        environment_id, tool_id, _label, _tooltip = MATRIX_COLUMNS[index.column() - 3]
        name = resource["name"]
        active = tool_id in self.assignments.get(name, {}).get(environment_id, [])
        state = Qt.CheckState.Unchecked.value if active else Qt.CheckState.Checked.value
        self._toggle_tool(name, environment_id, tool_id, state)
        self._refresh_matrix_cell(row, resource, environment_id, tool_id)
        payload = {"action": "sync" if state == Qt.CheckState.Checked.value else "remove", "names": [name], "assignments": {name: {environment_id: [tool_id]}}, "commitTargets": deepcopy(self.assignments.get(name, {}))}
        self.sync_requested.emit(self.kind, payload)

    def _handle_upgrade_clicked(self, index: QModelIndex) -> None:
        row = index.row()
        if row >= len(self._visible_rows):
            return
        resource = self._visible_rows[row]
        if not self._is_upgradeable_row(resource):
            return
        name = resource["name"]
        targets = deepcopy(self.assignments.get(name, {}))
        if not self._has_assignments(targets):
            return
        self.sync_requested.emit(
            self.kind,
            {
                "action": "upgrade",
                "names": [name],
                "assignments": {name: targets},
            },
        )

    def _has_assignments(self, targets: dict[str, list[str]]) -> bool:
        return any(targets.get(environment_id) for environment_id in ("windows", "wsl"))

    def _apply_matrix_item_state(
        self,
        item: QTableWidgetItem,
        row: dict[str, object],
        environment_id: str,
        tool_id: str,
    ) -> None:
        active = tool_id in self.assignments.get(row["name"], {}).get(environment_id, [])
        entry = find_matrix_entry(row, environment_id, tool_id)
        state = entry["state"] if active and entry else ("healthy" if active else "idle")
        item.setData(LOGO_ACTIVE_ROLE, active)
        item.setData(LOGO_STATE_ROLE, state)
        item.setData(LOGO_TOOL_ROLE, tool_id)
        item.setToolTip(matrix_tooltip(environment_id, tool_id, active, entry if active else None))

    def _refresh_matrix_cell(
        self,
        row_index: int,
        row: dict[str, object],
        environment_id: str,
        tool_id: str,
    ) -> None:
        column = matrix_column(environment_id, tool_id)
        item = self.table.item(row_index, column)
        if item is None:
            return
        self._apply_matrix_item_state(item, row, environment_id, tool_id)
        index = self.table.model().index(row_index, column)
        self.table.model().dataChanged.emit(index, index)
