from copy import deepcopy
from dataclasses import dataclass
from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from ...core.tool_definitions import TOOL_IDS
from ..event_filters import WheelBlocker
from ..logo_matrix import (
    LOGO_ACTIVE_ROLE,
    LOGO_BUSY_ROLE,
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
from ..feedback import confirm_destructive
from ..pagination import Pager, paginate
from .resource_selection import PageSelection
from ..widgets import ActionButton, CardFrame, FrozenRightTableWidget, configure_table
from .skill_upstream_dialogs import AddSkillFromUrlDialog, SetSkillUrlDialog
RESOURCE_ROWS_PER_PAGE = 10
NAME_CELL_PREVIEW_CHARS = 90
ROW_HEIGHT_DEFAULT = 42
ROW_HEIGHT_WITH_DESCRIPTION = 58
ROW_HEIGHT_CHILD = 36
ENVIRONMENT_IDS = ("windows", "wsl")
_ITEM_RESOURCE = "resource"
_ITEM_CHILD = "child"


@dataclass(frozen=True)
class PendingResourceToggle:
    busy_key: str
    name: str
    previous_assignments: dict[str, list[str]] | None
    start_revision: int


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


def _build_expandable_name_cell(
    name: str,
    description: str,
    tooltip: str,
    expanded: bool,
    children_count: int,
    on_toggle,
) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 2, 0, 2)
    layout.setSpacing(2)
    top_row = QHBoxLayout()
    top_row.setSpacing(4)
    top_row.setContentsMargins(0, 0, 0, 0)
    toggle = QPushButton("\u25bc" if expanded else "\u25b6")
    toggle.setFixedSize(20, 20)
    toggle.setStyleSheet(
        "QPushButton { border: none; background: transparent;"
        " font-size: 10px; color: #6b7280; }"
        "QPushButton:hover { color: #3b82f6; }"
    )
    toggle.setCursor(Qt.CursorShape.PointingHandCursor)
    toggle.clicked.connect(on_toggle)
    top_row.addWidget(toggle)
    name_label = QLabel(name)
    name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    top_row.addWidget(name_label, 1)
    count_label = QLabel(f"({children_count})")
    count_label.setObjectName("muted")
    count_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    top_row.addWidget(count_label)
    layout.addLayout(top_row)
    if description.strip():
        desc_label = QLabel(_truncate(description, NAME_CELL_PREVIEW_CHARS))
        desc_label.setObjectName("muted")
        desc_label.setWordWrap(False)
        desc_label.setContentsMargins(24, 0, 0, 0)
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(desc_label)
    container.setToolTip(tooltip or name)
    return container


class ResourcePage(QWidget):
    rescan_requested = Signal(str)
    sync_requested = Signal(str, object)
    add_skill_requested = Signal(object)
    set_url_requested = Signal(object)
    check_upstream_requested = Signal(object)
    upgrade_upstream_requested = Signal(object)
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
        self._expanded_names: set[str] = set()
        self._display_items: list[dict[str, object]] = []
        self._busy_cells: set[str] = set()
        self._pending_cells: dict[str, PendingResourceToggle] = {}
        self._data_revision = 0
        self._upstream_inventory: list[dict[str, object]] = []
        self._upstreams: dict[str, dict[str, object]] = {}
        self._update_results: dict[str, dict[str, object]] = {}
        self._build_ui()
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        title = "Skills" if self.kind == "skills" else "Commands"
        layout.addWidget(self._build_toolbar_card())
        layout.addWidget(self._build_table_card(title), 1)
    def _build_toolbar_card(self) -> QWidget:
        card = CardFrame()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 1)
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"搜索 {self.kind} 名称或路径")
        self.search.textChanged.connect(self._handle_filter_changed)
        self.rescan_button = ActionButton("重新扫描", "secondary")
        self.sync_button = ActionButton("同步选中", "secondary")
        self.upgrade_button = ActionButton("全部升级", "secondary")
        self.remove_button = ActionButton("移除选中", "danger")
        self.rescan_button.clicked.connect(lambda: self.rescan_requested.emit(self.kind))
        self.sync_button.clicked.connect(self._emit_sync)
        self.upgrade_button.clicked.connect(self._emit_upgrade_all)
        self.remove_button.clicked.connect(self._emit_remove)
        col = 2
        grid.addWidget(self.search, 0, 0, 1, 2)
        grid.addWidget(self.rescan_button, 0, col); col += 1
        grid.addWidget(self.sync_button, 0, col); col += 1
        grid.addWidget(self.upgrade_button, 0, col); col += 1
        grid.addWidget(self.remove_button, 0, col); col += 1
        self.add_skill_button = None
        self.set_url_button = None
        self.check_button = None
        if self.kind == "skills":
            self.add_skill_button = ActionButton("新增 Skill", "secondary")
            self.set_url_button = ActionButton("设置 URL", "secondary")
            self.check_button = ActionButton("检查更新", "secondary")
            self.add_skill_button.clicked.connect(self._open_add_dialog)
            self.set_url_button.clicked.connect(self._open_set_url_dialog)
            self.check_button.clicked.connect(self._emit_check)
            grid.addWidget(self.add_skill_button, 0, col); col += 1
            grid.addWidget(self.set_url_button, 0, col); col += 1
            grid.addWidget(self.check_button, 0, col); col += 1
        self.meta = QLabel("0 条记录")
        self.meta.setObjectName("muted")
        grid.addWidget(self.meta, 1, 0, 1, col)
        card.body_layout.addLayout(grid)
        return card
    def _build_table_card(self, title: str) -> QWidget:
        card = CardFrame(f"{title} 列表", "查看资源状态和工具分配。")
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
        fixed_columns = {0: 48, 2: 72}
        for column, width in fixed_columns.items():
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        matrix_header = frozen_view.horizontalHeader()
        for column in range(3, len(TABLE_HEADERS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            matrix_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, 68)
            frozen_view.setColumnWidth(column, 68)
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
                    item.setToolTip("操作：copy 模式下，源比目标新时可升级。")
        self._logo_delegate = ToolLogoDelegate(self.table)
        self._frozen_logo_delegate = ToolLogoDelegate(frozen_view)
        for column in range(3, MATRIX_END_COLUMN + 1):
            self.table.setItemDelegateForColumn(column, self._logo_delegate)
            frozen_view.setItemDelegateForColumn(column, self._frozen_logo_delegate)
        self.table.clicked.connect(self._handle_matrix_clicked)
        frozen_view.clicked.connect(self._handle_matrix_clicked)
        self.table.sync_frozen_view()
        self.pager = Pager()
        self.pager.page_requested.connect(self._set_page)
        card.body_layout.addWidget(self.pager)
        card.body_layout.setSpacing(8)
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
        if not names:
            return
        label = "Skills" if self.kind == "skills" else "Commands"
        if not confirm_destructive(
            self,
            f"确认移除 {label}",
            f"即将移除 {len(names)} 个 {label}，此操作不可撤销。\n\n确定继续？",
        ):
            return
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
        if self.kind == "skills":
            upstream_names = [
                name for name, upstream in self._upstreams.items()
                if upstream.get("url")
            ]
            if upstream_names:
                self.upgrade_upstream_requested.emit({"names": upstream_names})
                return
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
        self._data_revision += 1
        self.rows = deepcopy(rows)
        self.assignments = {
            row["name"]: deepcopy(row["effectiveTargets"])
            for row in rows
            if self._has_assignments(row["effectiveTargets"])
        }
        self._pending_cells = {
            key: pending
            for key, pending in self._pending_cells.items()
            if key in self._busy_cells
        }
        existing_names = {row["name"] for row in rows}
        self.selected_names &= existing_names
        self._expanded_names &= existing_names
        self._rebuild_table()

    def get_assignments(self) -> dict[str, dict[str, list[str]]]:
        return {name: targets for name, targets in self.assignments.items() if self._has_assignments(targets)}

    def get_selected_names(self) -> list[str]:
        visible = {row["name"] for row in self._filtered_rows()}
        return sorted(self.selected_names & visible)

    def set_busy(
        self,
        rescan_busy: bool,
        sync_busy: bool,
        cell_busy_keys: set[str] = frozenset(),
        upstream_busy: bool = False,
    ) -> None:
        next_busy_cells = set(cell_busy_keys)
        busy_changed = next_busy_cells != self._busy_cells
        released_keys = self._busy_cells - next_busy_cells
        self._busy_cells = next_busy_cells
        self._resolve_released_busy_cells(released_keys)
        self.rescan_button.set_busy(rescan_busy)
        self.sync_button.set_busy(sync_busy)
        self.upgrade_button.set_busy(sync_busy or upstream_busy)
        self.remove_button.set_busy(sync_busy)
        if self.add_skill_button:
            self.add_skill_button.set_busy(upstream_busy)
        if self.set_url_button:
            self.set_url_button.set_busy(upstream_busy)
        if self.check_button:
            self.check_button.set_busy(upstream_busy)
        if busy_changed and not released_keys:
            self._rebuild_table()
            return
        self.table.viewport().update()
        self.table.frozen_view().viewport().update()

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
        self._display_items = self._build_display_items()
        self._updating_table = True
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._display_items))
        for row_index, display_item in enumerate(self._display_items):
            if display_item["type"] == _ITEM_RESOURCE:
                self._fill_row(row_index, display_item["row"])
            else:
                self._fill_child_row(row_index, display_item)
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
            for env_id in ENVIRONMENT_IDS:
                for tool_id in tools:
                    entry = find_matrix_entry(row, env_id, tool_id)
                    if self._has_visible_target(row, env_id, tool_id, entry):
                        stats[env_id][tool_id] += 1
        return stats

    def _update_meta(self) -> None:
        self.meta.setText(f"{len(self.rows)} 条 · 已选 {len(self.selected_names)} 项")

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
        action_text = self._action_column_text(row)
        action_item = QTableWidgetItem(action_text)
        action_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        action_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        action_item.setToolTip(self._action_column_tooltip(row))
        self.table.setItem(row_index, ACTION_COLUMN, action_item)
        self._sync_row_height(row_index, row.get("description", ""))

    def _set_select_cell(self, row_index: int, name: str) -> None:
        checkbox = QCheckBox()
        checkbox.setChecked(name in self.selected_names)
        checkbox.stateChanged.connect(lambda state, item=name: self._toggle_selected(item, state))
        wrapper = QWidget()
        wrapper.setToolTip("勾选后可执行「同步选中 / 移除选中」")
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
        children = row.get("children", [])
        if children:
            expanded = name in self._expanded_names
            cell = _build_expandable_name_cell(
                name, description, tooltip, expanded, len(children),
                lambda _=False, n=name: self._toggle_expanded(n),
            )
        else:
            cell = _build_name_cell(name, description, tooltip)
        self.table.setCellWidget(row_index, 1, cell)

    def _sync_row_height(self, row_index: int, description: str) -> None:
        height = ROW_HEIGHT_WITH_DESCRIPTION if description.strip() else ROW_HEIGHT_DEFAULT
        self.table.setRowHeight(row_index, height)

    def _toggle_expanded(self, name: str) -> None:
        if name in self._expanded_names:
            self._expanded_names.discard(name)
        else:
            self._expanded_names.add(name)
        self._rebuild_table()

    def _build_display_items(self) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for row in self._visible_rows:
            items.append({"type": _ITEM_RESOURCE, "row": row})
            children = row.get("children", [])
            if children and row["name"] in self._expanded_names:
                for child in children:
                    items.append({
                        "type": _ITEM_CHILD,
                        "childName": child,
                        "parentRow": row,
                    })
        return items

    def _fill_child_row(self, row_index: int, display_item: dict[str, object]) -> None:
        self.table.setCellWidget(row_index, 0, QWidget())
        child_name = str(display_item["childName"])
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(28, 0, 0, 0)
        layout.setSpacing(0)
        label = QLabel(child_name)
        label.setObjectName("muted")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(label)
        container.setToolTip(child_name)
        self.table.setCellWidget(row_index, 1, container)
        type_item = QTableWidgetItem("")
        type_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row_index, 2, type_item)
        for offset in range(len(MATRIX_COLUMNS)):
            cell = QTableWidgetItem()
            cell.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_index, offset + 3, cell)
        action_item = QTableWidgetItem("")
        action_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row_index, ACTION_COLUMN, action_item)
        self.table.setRowHeight(row_index, ROW_HEIGHT_CHILD)

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
        entries = row.get("entries", [])
        if any(entry.get("state") == "outdated" for entry in entries):
            return True
        has_visible_target = any(bool(entry.get("targetExists")) for entry in entries)
        return has_visible_target and any(entry.get("state") == "missing" for entry in entries)

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

    def _busy_key(self, name: str, environment_id: str, tool_id: str) -> str:
        return f"resourceCell:{self.kind}:{name}:{environment_id}:{tool_id}"

    def _resolve_released_busy_cells(self, released_keys: set[str]) -> None:
        for busy_key in released_keys:
            pending = self._pending_cells.pop(busy_key, None)
            if pending is None:
                continue
            if self._data_revision > pending.start_revision:
                continue
            if pending.previous_assignments:
                self.assignments[pending.name] = deepcopy(pending.previous_assignments)
            else:
                self.assignments.pop(pending.name, None)
        if released_keys:
            self._rebuild_table()

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
        row = index.row()
        if row >= len(self._display_items):
            return
        if self._display_items[row]["type"] != _ITEM_RESOURCE:
            return
        if is_action_cell(index):
            self._handle_upgrade_clicked(index)
            return
        if not is_matrix_cell(index):
            return
        resource = self._display_items[row]["row"]
        environment_id, tool_id, _label, _tooltip = MATRIX_COLUMNS[index.column() - 3]
        name = resource["name"]
        busy_key = self._busy_key(name, environment_id, tool_id)
        if busy_key in self._busy_cells:
            return
        active = tool_id in self.assignments.get(name, {}).get(environment_id, [])
        state = Qt.CheckState.Unchecked.value if active else Qt.CheckState.Checked.value
        self._pending_cells[busy_key] = PendingResourceToggle(
            busy_key=busy_key,
            name=name,
            previous_assignments=deepcopy(self.assignments.get(name)),
            start_revision=self._data_revision,
        )
        self._toggle_tool(name, environment_id, tool_id, state)
        self._refresh_matrix_cell(row, resource, environment_id, tool_id)
        payload = {
            "action": "sync" if state == Qt.CheckState.Checked.value else "remove",
            "names": [name],
            "assignments": {name: {environment_id: [tool_id]}},
            "commitTargets": deepcopy(self.assignments.get(name, {})),
            "busyKey": busy_key,
        }
        self.sync_requested.emit(self.kind, payload)

    def _handle_upgrade_clicked(self, index: QModelIndex) -> None:
        row_idx = index.row()
        if row_idx >= len(self._display_items):
            return
        if self._display_items[row_idx]["type"] != _ITEM_RESOURCE:
            return
        resource = self._display_items[row_idx]["row"]
        name = resource["name"]

        if self.kind == "skills":
            upstream = self._upstreams.get(name, {})
            url = str(upstream.get("url") or "").strip()
            if not url:
                dialog = SetSkillUrlDialog(f"设置 URL：{name}", self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                url = dialog.url()
                if not url:
                    return
                self.set_url_requested.emit({"names": [name], "url": url})
                return
            update = self._update_results.get(name, {})
            if not update:
                self.check_upstream_requested.emit({"names": [name]})
                return
            has_update = bool(update.get("latestCommit")) and update.get("latestCommit") != update.get("installedCommit")
            if has_update:
                self.upgrade_upstream_requested.emit({"names": [name]})
                return

        if not self._is_upgradeable_row(resource):
            return
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
        busy = self._busy_key(str(row.get("name", "")), environment_id, tool_id) in self._busy_cells
        entry = find_matrix_entry(row, environment_id, tool_id)
        active = self._has_visible_target(row, environment_id, tool_id, entry)
        state = "busy" if busy else (entry["state"] if entry else ("detected" if active else "idle"))
        item.setData(LOGO_ACTIVE_ROLE, active)
        item.setData(LOGO_STATE_ROLE, state)
        item.setData(LOGO_TOOL_ROLE, tool_id)
        item.setData(LOGO_BUSY_ROLE, busy)
        item.setToolTip("处理中…" if busy else matrix_tooltip(environment_id, tool_id, active, entry))

    def _has_visible_target(
        self,
        row: dict[str, object],
        environment_id: str,
        tool_id: str,
        entry: dict[str, object] | None,
    ) -> bool:
        if entry is not None:
            return bool(entry.get("targetExists"))
        return tool_id in self.assignments.get(row["name"], {}).get(environment_id, [])

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

    def _action_column_text(self, row: dict[str, object]) -> str:
        if self.kind != "skills":
            return "升级" if self._is_upgradeable_row(row) else ""
        name = row["name"]
        upstream = self._upstreams.get(name, {})
        url = str(upstream.get("url") or "").strip()
        if not url:
            return "设置 URL"
        update = self._update_results.get(name, {})
        if not update:
            return "检查"
        has_update = bool(update.get("latestCommit")) and update.get("latestCommit") != update.get("installedCommit")
        if has_update:
            return "升级"
        if self._is_upgradeable_row(row):
            return "升级"
        return "\u2713"

    def _action_column_tooltip(self, row: dict[str, object]) -> str:
        if self.kind != "skills":
            return "升级：同步缺失或有新版本的条目，跳过目标比源新的条目。"
        name = row["name"]
        upstream = self._upstreams.get(name, {})
        url = str(upstream.get("url") or "").strip()
        if not url:
            return "点击设置上游 URL"
        update = self._update_results.get(name, {})
        if not update:
            return "点击检查远程更新"
        has_update = bool(update.get("latestCommit")) and update.get("latestCommit") != update.get("installedCommit")
        if has_update:
            installed = str(update.get("installedCommit") or "未记录")[:8]
            latest = str(update.get("latestCommit") or "")[:8]
            return f"有新版本: {installed} → {latest}"
        if self._is_upgradeable_row(row):
            return "本地文件有更新可同步"
        return "已是最新"

    def set_upstream_context(
        self,
        inventory: list[dict[str, object]],
        upstreams: dict[str, dict[str, object]],
    ) -> None:
        self._upstream_inventory = deepcopy(inventory) if isinstance(inventory, list) else []
        self._upstreams = deepcopy(upstreams) if isinstance(upstreams, dict) else {}
        self._rebuild_table()

    def set_update_results(self, results: list[dict[str, object]]) -> None:
        self._update_results = {
            str(item.get("name")): deepcopy(item)
            for item in results
            if isinstance(item, dict)
        }
        self._rebuild_table()

    def _open_add_dialog(self) -> None:
        dialog = AddSkillFromUrlDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dialog.payload()
        if not payload["name"]:
            QMessageBox.warning(self, "新增失败", "请填写 Skill 名称。")
            return
        if not payload["url"]:
            QMessageBox.warning(self, "新增失败", "请填写 URL。")
            return
        self.add_skill_requested.emit(payload)

    def _open_set_url_dialog(self) -> None:
        names = self.get_selected_names()
        if not names:
            QMessageBox.warning(self, "设置失败", "请先选择 Skill。")
            return
        dialog = SetSkillUrlDialog(f"设置 URL（{len(names)} 个）", self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        url = dialog.url()
        if not url:
            QMessageBox.warning(self, "设置失败", "请填写 URL。")
            return
        self.set_url_requested.emit({"names": names, "url": url})

    def _emit_check(self) -> None:
        names = self.get_selected_names()
        if not names:
            QMessageBox.warning(self, "检查失败", "请先选择 Skill。")
            return
        self.check_upstream_requested.emit({"names": names})
