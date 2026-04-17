from copy import deepcopy

from dataclasses import dataclass

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.resource_operations import aggregate_states
from ..busy import busy_indicator_driver
from ..event_filters import WheelBlocker
from ..header_views import GroupedHeaderView
from ..logo_matrix import LOGO_ACTIVE_ROLE, LOGO_BUSY_ROLE, LOGO_STATE_ROLE, LOGO_TOOL_ROLE, logo_root
from ..pagination import Pager, paginate
from ..pages.resource_selection import PageSelection
from ..theme import SURFACE, tint
from ..widgets import ActionButton, CardFrame, configure_table

ROWS_PER_PAGE = 8
BADGE_SIZE = QSize(40, 24)
ICON_SIZE = 14
ROW_HEIGHT_PARENT = 46
ROW_HEIGHT_CHILD = 40
COL_SELECT = 0
COL_NAME = 1
COL_PATH = 2
MATRIX_COLUMNS = (
    ("windows", "claude", "Claude"),
    ("windows", "codex", "Codex"),
    ("windows", "both", "一起"),
    ("wsl", "claude", "Claude"),
    ("wsl", "codex", "Codex"),
    ("wsl", "both", "一起"),
)
MATRIX_START = 3
TABLE_HEADERS = ("选中", "项目 / Skill", "路径 / 配置", *(item[2] for item in MATRIX_COLUMNS))
GROUPS = (("WIN", (3, 4, 5)), ("WSL", (6, 7, 8)))
TOOL_LABELS = {"claude": "Claude", "codex": "Codex", "both": "Claude + Codex"}
_ITEM_PROJECT = "project"
_ITEM_SKILL = "skill"
BUSY_BORDER = "#93c5fd"
BUSY_BG = "#eff6ff"


@dataclass(frozen=True)
class PendingProjectSkillToggle:
    busy_key: str
    project_id: str
    skill_name: str
    previous_assignments: dict[str, list[str]] | None
    start_revision: int


def _skill_key(project_id: str, skill_name: str) -> str:
    return f"{project_id}::{skill_name}"


def _tooltip_for_skill(skill: dict[str, object]) -> str:
    parts = [str(skill.get("description") or "").strip(), str(skill.get("path") or "").strip()]
    return "\n\n".join(part for part in parts if part)


def _project_paths_summary(project: dict[str, object]) -> str:
    return "\n".join(
        [
            f"源: {project.get('skillSourceDir') or '未配置'}",
            f"WIN: {project.get('windowsProjectRoot') or '未配置'}",
            f"WSL: {project.get('wslProjectRoot') or '未配置'}",
        ]
    )


def _state_for_pair(
    row: dict[str, object],
    page_assignments: dict[str, dict[str, dict[str, list[str]]]],
    environment_id: str,
) -> tuple[bool, str]:
    states: list[dict[str, str]] = []
    active_tools = 0
    for tool_id in ("claude", "codex"):
        entry = _find_entry(row, environment_id, tool_id)
        active = _has_active_target(row, page_assignments, environment_id, tool_id, entry)
        if active:
            active_tools += 1
        states.append({"state": entry["state"] if entry else ("detected" if active else "idle"), "message": ""})
    if active_tools == 2 and all(state["state"] == "detected" for state in states):
        return True, "detected"
    if active_tools == 0 and all(state["state"] == "idle" for state in states):
        return False, "idle"
    summary = aggregate_states(states)
    return active_tools == 2, str(summary["state"])


def _find_entry(
    row: dict[str, object],
    environment_id: str,
    tool_id: str,
) -> dict[str, object] | None:
    for entry in row.get("entries", []):
        if entry["environmentId"] == environment_id and entry["toolId"] == tool_id:
            return entry
    return None


def _has_active_target(
    row: dict[str, object],
    page_assignments: dict[str, dict[str, dict[str, list[str]]]],
    environment_id: str,
    tool_id: str,
    entry: dict[str, object] | None,
) -> bool:
    if entry is not None:
        return bool(entry.get("targetExists"))
    project_assignments = page_assignments.get(str(row.get("projectId") or ""), {})
    skill_assignments = project_assignments.get(str(row.get("name") or ""), {})
    return tool_id in skill_assignments.get(environment_id, [])


def _cell_tooltip(
    row: dict[str, object],
    page_assignments: dict[str, dict[str, dict[str, list[str]]]],
    environment_id: str,
    tool_key: str,
) -> str:
    prefix = "Windows" if environment_id == "windows" else "WSL"
    if tool_key == "both":
        active, state = _state_for_pair(row, page_assignments, environment_id)
        message = "同时同步" if active else "未同步"
        if state == "partial":
            message = "部分已同步"
        if state == "detected":
            message = "已检测到目标"
        return f"{prefix} / Claude + Codex · {message}"
    entry = _find_entry(row, environment_id, tool_key)
    active = _has_active_target(row, page_assignments, environment_id, tool_key, entry)
    if entry:
        return f"{prefix} / {TOOL_LABELS[tool_key]} · {entry.get('message') or entry['state']}"
    if active:
        return f"{prefix} / {TOOL_LABELS[tool_key]} · 已检测到目标"
    return f"{prefix} / {TOOL_LABELS[tool_key]} · 未同步"


class ProjectSkillLogoDelegate(QStyledItemDelegate):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmaps = self._load_pixmaps()
        self._busy_driver = busy_indicator_driver()
        self._busy_driver.frame_changed.connect(self._handle_busy_frame)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        base = super().sizeHint(option, index)
        return QSize(max(base.width(), BADGE_SIZE.width() + 12), max(base.height(), BADGE_SIZE.height() + 8))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        tool_id = str(index.data(LOGO_TOOL_ROLE) or "")
        if not tool_id:
            super().paint(painter, option, index)
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_badge(
            painter,
            option,
            index,
            tool_id,
            bool(index.data(LOGO_ACTIVE_ROLE)),
            str(index.data(LOGO_STATE_ROLE) or "idle"),
        )
        painter.restore()

    def _paint_badge(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        tool_id: str,
        active: bool,
        state: str,
    ) -> None:
        busy = bool(index.data(LOGO_BUSY_ROLE))
        border, background = self._badge_colors(state, active, busy)
        badge_rect = self._badge_rect(option)
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(badge_rect, 8, 8)
        self._draw_logo(painter, badge_rect, tool_id, active, busy)
        if not active and not busy:
            overlay = QColor("#c5ced8")
            overlay.setAlpha(108)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(overlay)
            painter.drawRoundedRect(badge_rect, 8, 8)
        if busy:
            self._draw_spinner(painter, badge_rect)

    def _draw_logo(self, painter: QPainter, badge_rect: QRect, tool_id: str, active: bool, busy: bool) -> None:
        if not active and not busy:
            painter.setOpacity(0.42)
        if tool_id == "both":
            self._draw_dual_logo(painter, badge_rect)
        else:
            pixmap = self._pixmaps.get(tool_id)
            if pixmap is not None:
                icon = pixmap.scaled(ICON_SIZE, ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                left = badge_rect.x() + (badge_rect.width() - icon.width()) // 2
                top = badge_rect.y() + (badge_rect.height() - icon.height()) // 2
                painter.drawPixmap(left, top, icon)
        painter.setOpacity(1.0)

    def _draw_dual_logo(self, painter: QPainter, badge_rect: QRect) -> None:
        claude = self._pixmaps.get("claude")
        codex = self._pixmaps.get("codex")
        if claude is None or codex is None:
            return
        left_icon = claude.scaled(12, 12, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        right_icon = codex.scaled(12, 12, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        gap = 3
        total_width = left_icon.width() + right_icon.width() + gap
        left = badge_rect.x() + (badge_rect.width() - total_width) // 2
        top = badge_rect.y() + (badge_rect.height() - max(left_icon.height(), right_icon.height())) // 2
        painter.drawPixmap(left, top, left_icon)
        painter.drawPixmap(left + left_icon.width() + gap, top, right_icon)

    def _badge_rect(self, option: QStyleOptionViewItem) -> QRect:
        left = option.rect.x() + (option.rect.width() - BADGE_SIZE.width()) // 2
        top = option.rect.y() + (option.rect.height() - BADGE_SIZE.height()) // 2
        return QRect(left, top, BADGE_SIZE.width(), BADGE_SIZE.height())

    def _badge_colors(self, state: str, active: bool, busy: bool = False) -> tuple[str, str]:
        if busy:
            return BUSY_BORDER, BUSY_BG
        if not active:
            return "#d3dce6", "#edf1f5"
        palette = {
            "healthy": "#16a34a",
            "outdated": "#2563eb",
            "conflict": "#dc2626",
            "ahead": "#ea580c",
            "environment_error": "#b45309",
            "source_missing": "#dc2626",
            "partial": "#2563eb",
            "detected": "#2563eb",
            "idle": "#94a3b8",
            "missing": "#94a3b8",
        }
        foreground = palette.get(state, "#16a34a")
        return tint(foreground, 96), SURFACE

    def _draw_spinner(self, painter: QPainter, badge_rect: QRect) -> None:
        spinner_rect = QRect(
            badge_rect.right() - 13,
            badge_rect.y() + 2,
            9,
            9,
        )
        pen = QPen(QColor("#2563eb"), 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        start_angle = (self._busy_driver.frame * 90) * 16
        painter.drawArc(spinner_rect, start_angle, 220 * 16)

    def _handle_busy_frame(self, _frame: int) -> None:
        parent = self.parent()
        if isinstance(parent, QAbstractItemView):
            parent.viewport().update()

    def _load_pixmaps(self) -> dict[str, QPixmap]:
        root = logo_root()
        mapping = {"claude": "Claude.png", "codex": "OpenAI.png"}
        result: dict[str, QPixmap] = {}
        for tool_id, filename in mapping.items():
            pixmap = QPixmap(str(root / filename))
            if not pixmap.isNull():
                result[tool_id] = pixmap
        return result


class ProjectSkillsPage(QWidget):
    refresh_requested = Signal()
    sync_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.projects: list[dict[str, object]] = []
        self.assignments: dict[str, dict[str, dict[str, list[str]]]] = {}
        self.selected_keys: set[str] = set()
        self._display_items: list[dict[str, object]] = []
        self._visible_projects: list[dict[str, object]] = []
        self._expanded_projects: set[str] = set()
        self._busy_cells: set[str] = set()
        self._pending_cells: dict[str, PendingProjectSkillToggle] = {}
        self._data_revision = 0
        self._page_index = 0
        self._page_size = ROWS_PER_PAGE
        self._updating_table = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_toolbar_card())
        layout.addWidget(self._build_table_card(), 1)

    def _build_toolbar_card(self) -> QWidget:
        card = CardFrame("项目级 Skills", "把仓库内项目专用的 skill 同步到目标项目目录的 .agents 或 .claude 下。")
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索项目名、Skill 名或路径")
        self.search.textChanged.connect(self._handle_filter_changed)
        self.refresh_button = ActionButton("重新扫描", "secondary")
        self.sync_button = ActionButton("同步选中", "secondary")
        self.remove_button = ActionButton("移除选中", "danger")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.sync_button.clicked.connect(self._emit_sync_selected)
        self.remove_button.clicked.connect(self._emit_remove_selected)
        row.addWidget(self.search, 1)
        row.addWidget(self.refresh_button)
        row.addWidget(self.sync_button)
        row.addWidget(self.remove_button)
        self.meta = QLabel("0 个项目")
        self.meta.setObjectName("muted")
        card.body_layout.addLayout(row)
        card.body_layout.addWidget(self.meta)
        return card

    def _build_table_card(self) -> QWidget:
        card = CardFrame("项目 Skills 列表", "按项目分组显示；点击图标可单独同步或移除。")
        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self.table.setHorizontalHeader(GroupedHeaderView(GROUPS, self.table))
        configure_table(self.table, stretch_columns=(1, 2))
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.horizontalHeader().setSectionResizeMode(COL_SELECT, self.table.horizontalHeader().ResizeMode.Fixed)
        self.table.setColumnWidth(COL_SELECT, 48)
        for column in range(MATRIX_START, len(TABLE_HEADERS)):
            self.table.horizontalHeader().setSectionResizeMode(column, self.table.horizontalHeader().ResizeMode.Fixed)
            self.table.setColumnWidth(column, 72)
        self._wheel_blocker = WheelBlocker(self.table)
        self._wheel_blocker.set_enabled(True)
        self.table.viewport().installEventFilter(self._wheel_blocker)
        self._page_selection = PageSelection(self.table, self.selected_keys, self._visible_keys, self._update_meta)
        self._page_selection.configure_header_checkbox()
        self._logo_delegate = ProjectSkillLogoDelegate(self.table)
        for column in range(MATRIX_START, len(TABLE_HEADERS)):
            self.table.setItemDelegateForColumn(column, self._logo_delegate)
        self.table.clicked.connect(self._handle_table_clicked)
        self.pager = Pager(show_stats=False)
        self.pager.page_requested.connect(self._set_page)
        card.body_layout.addWidget(self.pager)
        card.body_layout.addWidget(self.table, 1)
        return card

    def set_context(self, projects: list[dict[str, object]]) -> None:
        self._data_revision += 1
        self.projects = deepcopy(projects)
        self.assignments = self._initial_assignments(self.projects)
        self._pending_cells = {
            key: pending
            for key, pending in self._pending_cells.items()
            if key in self._busy_cells
        }
        ids = {project["id"] for project in self.projects}
        self._expanded_projects = (self._expanded_projects & ids) | ids
        valid_keys = {
            _skill_key(project["id"], skill["name"])
            for project in self.projects
            for skill in project.get("skills", [])
        }
        self.selected_keys &= valid_keys
        self._rebuild_table()

    def set_busy(
        self,
        refresh_busy: bool,
        sync_busy: bool,
        cell_busy_keys: set[str] = frozenset(),
    ) -> None:
        next_busy_cells = set(cell_busy_keys)
        busy_changed = next_busy_cells != self._busy_cells
        released_keys = self._busy_cells - next_busy_cells
        self._busy_cells = next_busy_cells
        self._resolve_released_busy_cells(released_keys)
        self.refresh_button.set_busy(refresh_busy)
        self.sync_button.set_busy(sync_busy)
        self.remove_button.set_busy(sync_busy)
        if busy_changed and not released_keys:
            self._rebuild_table()
            return
        self.table.viewport().update()

    def _initial_assignments(
        self,
        projects: list[dict[str, object]],
    ) -> dict[str, dict[str, dict[str, list[str]]]]:
        assignments: dict[str, dict[str, dict[str, list[str]]]] = {}
        for project in projects:
            skills = project.get("skills", [])
            skill_assignments = {
                skill["name"]: deepcopy(skill["effectiveTargets"])
                for skill in skills
                if isinstance(skill, dict) and any(skill.get("effectiveTargets", {}).values())
            }
            if skill_assignments:
                assignments[project["id"]] = skill_assignments
        return assignments

    def _busy_key(
        self,
        project_id: str,
        skill_name: str,
        environment_id: str,
        tool_key: str,
    ) -> str:
        return f"projectSkillCell:{project_id}:{skill_name}:{environment_id}:{tool_key}"

    def _resolve_released_busy_cells(self, released_keys: set[str]) -> None:
        for busy_key in released_keys:
            pending = self._pending_cells.pop(busy_key, None)
            if pending is None:
                continue
            if self._data_revision > pending.start_revision:
                continue
            project_assignments = self.assignments.get(pending.project_id, {})
            if pending.previous_assignments:
                project_assignments[pending.skill_name] = deepcopy(pending.previous_assignments)
                self.assignments[pending.project_id] = project_assignments
                continue
            project_assignments.pop(pending.skill_name, None)
            if project_assignments:
                self.assignments[pending.project_id] = project_assignments
            else:
                self.assignments.pop(pending.project_id, None)
        if released_keys:
            self._rebuild_table()

    def _handle_filter_changed(self) -> None:
        self._page_index = 0
        self._rebuild_table()

    def _filtered_projects(self) -> list[dict[str, object]]:
        query = self.search.text().strip().lower()
        if not query:
            return self.projects
        filtered: list[dict[str, object]] = []
        for project in self.projects:
            project_text = "\n".join(
                [
                    str(project.get("id") or ""),
                    str(project.get("skillSourceDir") or ""),
                    str(project.get("windowsProjectRoot") or ""),
                    str(project.get("wslProjectRoot") or ""),
                ]
            ).lower()
            if query in project_text:
                filtered.append(project)
                continue
            skills = [
                skill for skill in project.get("skills", [])
                if query in str(skill.get("name") or "").lower() or query in str(skill.get("path") or "").lower()
            ]
            if skills:
                filtered.append({**project, "skills": skills})
        return filtered

    def _rebuild_table(self) -> None:
        rows = self._filtered_projects()
        self._visible_projects, self._page_index, page_count, total = paginate(rows, self._page_index, self._page_size)
        self._display_items = self._build_display_items()
        self._render_table()
        self.pager.set_state(self._page_index, page_count, total)
        self._update_meta()

    def _build_display_items(self) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for project in self._visible_projects:
            items.append({"type": _ITEM_PROJECT, "project": project})
            if project["id"] not in self._expanded_projects:
                continue
            for skill in project.get("skills", []):
                items.append({"type": _ITEM_SKILL, "project": project, "skill": skill})
        return items

    def _render_table(self) -> None:
        self._updating_table = True
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._display_items))
        for row_index, item in enumerate(self._display_items):
            if item["type"] == _ITEM_PROJECT:
                self._fill_project_row(row_index, item["project"])
            else:
                self._fill_skill_row(row_index, item["project"], item["skill"])
        self.table.blockSignals(False)
        self._updating_table = False
        self._page_selection.update_header_state()

    def _fill_project_row(self, row_index: int, project: dict[str, object]) -> None:
        self.table.setCellWidget(row_index, COL_SELECT, QWidget())
        self.table.setCellWidget(row_index, COL_NAME, self._project_name_cell(project))
        path_item = QTableWidgetItem(_project_paths_summary(project))
        path_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        path_item.setToolTip(_project_paths_summary(project))
        self.table.setItem(row_index, COL_PATH, path_item)
        for column in range(MATRIX_START, len(TABLE_HEADERS)):
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_index, column, item)
        self.table.setRowHeight(row_index, ROW_HEIGHT_PARENT)

    def _project_name_cell(self, project: dict[str, object]) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(2)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(4)
        toggle = QPushButton("▼" if project["id"] in self._expanded_projects else "▶")
        toggle.setFixedSize(20, 20)
        toggle.setStyleSheet("QPushButton { border: none; background: transparent; color: #6b7280; }")
        toggle.clicked.connect(lambda _=False, project_id=project["id"]: self._toggle_project(project_id))
        top.addWidget(toggle)
        top.addWidget(QLabel(project["id"]))
        count = QLabel(f"({len(project.get('skills', []))})")
        count.setObjectName("muted")
        top.addWidget(count)
        top.addStretch(1)
        layout.addLayout(top)
        if project.get("sourceMissing"):
            warn = QLabel("源目录不存在")
            warn.setObjectName("muted")
            layout.addWidget(warn)
        return container

    def _fill_skill_row(self, row_index: int, project: dict[str, object], skill: dict[str, object]) -> None:
        self.table.setCellWidget(row_index, COL_SELECT, self._skill_checkbox(project["id"], skill["name"]))
        self.table.setCellWidget(row_index, COL_NAME, self._skill_name_cell(skill))
        path_item = QTableWidgetItem(str(skill.get("path") or ""))
        path_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        path_item.setToolTip(_tooltip_for_skill(skill))
        self.table.setItem(row_index, COL_PATH, path_item)
        for offset, (environment_id, tool_key, _label) in enumerate(MATRIX_COLUMNS, start=MATRIX_START):
            self.table.setItem(row_index, offset, self._matrix_item(project["id"], skill, environment_id, tool_key))
        self.table.setRowHeight(row_index, ROW_HEIGHT_CHILD)

    def _skill_checkbox(self, project_id: str, skill_name: str) -> QWidget:
        key = _skill_key(project_id, skill_name)
        checkbox = QCheckBox()
        checkbox.setChecked(key in self.selected_keys)
        checkbox.stateChanged.connect(lambda state, item_key=key: self._toggle_selected(item_key, state))
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(checkbox)
        return wrapper

    def _skill_name_cell(self, skill: dict[str, object]) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(24, 0, 0, 0)
        layout.setSpacing(0)
        label = QLabel(skill["name"])
        label.setToolTip(_tooltip_for_skill(skill))
        layout.addWidget(label)
        return container

    def _matrix_item(
        self,
        project_id: str,
        row: dict[str, object],
        environment_id: str,
        tool_key: str,
    ) -> QTableWidgetItem:
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        name = str(row.get("name", ""))
        busy = self._busy_key(project_id, name, environment_id, tool_key) in self._busy_cells
        if tool_key == "both":
            busy = busy or any(
                self._busy_key(project_id, name, environment_id, child_tool) in self._busy_cells
                for child_tool in ("claude", "codex")
            )
        active, state = self._cell_state(project_id, row, environment_id, tool_key)
        if busy:
            state = "busy"
        item.setData(LOGO_ACTIVE_ROLE, active)
        item.setData(LOGO_STATE_ROLE, state)
        item.setData(LOGO_TOOL_ROLE, tool_key)
        item.setData(LOGO_BUSY_ROLE, busy)
        item.setToolTip(
            "处理中…"
            if busy
            else _cell_tooltip({**row, "projectId": project_id}, self.assignments, environment_id, tool_key)
        )
        return item

    def _cell_state(
        self,
        project_id: str,
        row: dict[str, object],
        environment_id: str,
        tool_key: str,
    ) -> tuple[bool, str]:
        if tool_key == "both":
            return _state_for_pair({**row, "projectId": project_id}, self.assignments, environment_id)
        entry = _find_entry(row, environment_id, tool_key)
        active = _has_active_target({**row, "projectId": project_id}, self.assignments, environment_id, tool_key, entry)
        return active, entry["state"] if entry else ("detected" if active else "idle")

    def _toggle_project(self, project_id: str) -> None:
        if project_id in self._expanded_projects:
            self._expanded_projects.discard(project_id)
        else:
            self._expanded_projects.add(project_id)
        self._rebuild_table()

    def _toggle_selected(self, item_key: str, state: int) -> None:
        if state == Qt.CheckState.Checked.value:
            self.selected_keys.add(item_key)
        else:
            self.selected_keys.discard(item_key)
        self._page_selection.update_header_state()
        self._update_meta()

    def _visible_keys(self) -> list[str]:
        keys: list[str] = []
        for item in self._display_items:
            if item["type"] != _ITEM_SKILL:
                continue
            keys.append(_skill_key(item["project"]["id"], item["skill"]["name"]))
        return keys

    def _update_meta(self) -> None:
        total_skills = sum(len(project.get("skills", [])) for project in self.projects)
        self.meta.setText(f"{len(self.projects)} 个项目 · {total_skills} 个 Skills · 已选 {len(self.selected_keys)} 项")

    def _set_page(self, index: int) -> None:
        self._page_index = index
        self._rebuild_table()

    def _handle_table_clicked(self, index: QModelIndex) -> None:
        if self._updating_table or index.column() < MATRIX_START:
            return
        if index.row() >= len(self._display_items):
            return
        item = self._display_items[index.row()]
        if item["type"] != _ITEM_SKILL:
            return
        environment_id, tool_key, _label = MATRIX_COLUMNS[index.column() - MATRIX_START]
        self._toggle_skill(item["project"], item["skill"], environment_id, tool_key)

    def _toggle_skill(
        self,
        project: dict[str, object],
        skill: dict[str, object],
        environment_id: str,
        tool_key: str,
    ) -> None:
        project_id = project["id"]
        busy_key = self._busy_key(project_id, skill["name"], environment_id, tool_key)
        if busy_key in self._busy_cells:
            return
        active, _state = self._cell_state(project_id, skill, environment_id, tool_key)
        tools = ("claude", "codex") if tool_key == "both" else (tool_key,)
        action = "remove" if active else "sync"
        self._pending_cells[busy_key] = PendingProjectSkillToggle(
            busy_key=busy_key,
            project_id=project_id,
            skill_name=skill["name"],
            previous_assignments=deepcopy(self.assignments.get(project_id, {}).get(skill["name"])),
            start_revision=self._data_revision,
        )
        self._mutate_assignment(project_id, skill["name"], environment_id, tools, not active)
        payload = {
            "action": action,
            "items": [{"projectId": project_id, "skillName": skill["name"]}],
            "assignments": {project_id: {skill["name"]: {environment_id: list(tools)}}},
            "commitAssignments": deepcopy(self.assignments),
            "busyKey": busy_key,
        }
        self.sync_requested.emit(payload)
        self._refresh_row({**skill, "projectId": project_id})

    def _mutate_assignment(
        self,
        project_id: str,
        skill_name: str,
        environment_id: str,
        tools: tuple[str, ...],
        enable: bool,
    ) -> None:
        project_assignments = deepcopy(self.assignments.get(project_id, {}))
        skill_assignments = deepcopy(project_assignments.get(skill_name, {}))
        selected = list(skill_assignments.get(environment_id, []))
        for tool_id in tools:
            if enable and tool_id not in selected:
                selected.append(tool_id)
            if not enable and tool_id in selected:
                selected.remove(tool_id)
        ordered = [tool_id for tool_id in ("claude", "codex") if tool_id in selected]
        if ordered:
            skill_assignments[environment_id] = ordered
        else:
            skill_assignments.pop(environment_id, None)
        if skill_assignments:
            project_assignments[skill_name] = skill_assignments
        else:
            project_assignments.pop(skill_name, None)
        if project_assignments:
            self.assignments[project_id] = project_assignments
        else:
            self.assignments.pop(project_id, None)

    def _refresh_row(self, skill: dict[str, object]) -> None:
        for row_index, item in enumerate(self._display_items):
            if item["type"] != _ITEM_SKILL:
                continue
            if item["project"]["id"] != skill["projectId"] or item["skill"]["name"] != skill["name"]:
                continue
            for offset, (environment_id, tool_key, _label) in enumerate(MATRIX_COLUMNS, start=MATRIX_START):
                self.table.setItem(
                    row_index,
                    offset,
                    self._matrix_item(item["project"]["id"], skill, environment_id, tool_key),
                )
            break

    def _emit_sync_selected(self) -> None:
        items = self._selected_items()
        if not items:
            return
        self.sync_requested.emit(
            {
                "action": "sync",
                "items": items,
                "assignments": self._selected_assignments(items),
                "commitAssignments": deepcopy(self.assignments),
            }
        )

    def _emit_remove_selected(self) -> None:
        items = self._selected_items()
        if not items:
            return
        current = self._selected_assignments(items)
        next_assignments = deepcopy(self.assignments)
        for item in items:
            project_id = item["projectId"]
            skill_name = item["skillName"]
            project_assignments = next_assignments.get(project_id, {})
            project_assignments.pop(skill_name, None)
            if not project_assignments:
                next_assignments.pop(project_id, None)
        self.assignments = next_assignments
        self.selected_keys -= {
            _skill_key(item["projectId"], item["skillName"])
            for item in items
        }
        self.sync_requested.emit(
            {
                "action": "remove",
                "items": items,
                "assignments": current,
                "commitAssignments": deepcopy(self.assignments),
            }
        )
        self._rebuild_table()

    def _selected_items(self) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for key in sorted(self.selected_keys):
            project_id, skill_name = key.split("::", 1)
            items.append({"projectId": project_id, "skillName": skill_name})
        return items

    def _selected_assignments(
        self,
        items: list[dict[str, str]],
    ) -> dict[str, dict[str, dict[str, list[str]]]]:
        result: dict[str, dict[str, dict[str, list[str]]]] = {}
        for item in items:
            project_id = item["projectId"]
            skill_name = item["skillName"]
            project_assignments = self.assignments.get(project_id, {})
            skill_assignments = project_assignments.get(skill_name, {})
            if not skill_assignments:
                continue
            result.setdefault(project_id, {})[skill_name] = deepcopy(skill_assignments)
        return result
