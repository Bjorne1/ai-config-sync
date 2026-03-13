from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)

from ..pagination import Pager, paginate
from ..widgets import ActionButton, CardFrame, configure_table
from .skill_upstream_dialogs import AddSkillFromUrlDialog, SetSkillUrlDialog


UPSTREAM_ROWS_PER_PAGE = 10

class SkillUpstreamPage(QWidget):
    add_requested = Signal(object)
    set_url_requested = Signal(object)
    check_requested = Signal(object)
    upgrade_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._inventory: list[dict[str, object]] = []
        self._upstreams: dict[str, dict[str, object]] = {}
        self._update_results: dict[str, dict[str, object]] = {}
        self._selected: set[str] = set()
        self._bulk_updating = False
        self._page_index = 0
        self._page_size = UPSTREAM_ROWS_PER_PAGE
        self._visible_rows: list[dict[str, object]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_toolbar_card())
        layout.addWidget(self._build_table_card(), 1)

    def _build_toolbar_card(self) -> QWidget:
        card = CardFrame("Skills 上游更新", "为 Skill 绑定 GitHub URL，检查和下载更新。")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 1)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索 skill 名称/路径/URL")
        self.search.textChanged.connect(self._handle_filter_changed)
        self.select_all = QCheckBox("全选当前页")
        self.select_all.stateChanged.connect(self._toggle_select_all)
        self.add_button = ActionButton("新增 Skill", "secondary")
        self.set_url_button = ActionButton("设置 URL", "secondary")
        self.check_button = ActionButton("检查更新", "secondary")
        self.upgrade_button = ActionButton("下载更新", "primary")
        self.add_button.clicked.connect(self._open_add_dialog)
        self.set_url_button.clicked.connect(self._open_set_url_dialog)
        self.check_button.clicked.connect(self._emit_check)
        self.upgrade_button.clicked.connect(self._emit_upgrade)
        grid.addWidget(self.search, 0, 0, 1, 2)
        grid.addWidget(self.select_all, 0, 2)
        grid.addWidget(self.add_button, 0, 3)
        grid.addWidget(self.set_url_button, 0, 4)
        grid.addWidget(self.check_button, 0, 5)
        grid.addWidget(self.upgrade_button, 0, 6)
        self.meta = QLabel("0 条记录")
        self.meta.setObjectName("muted")
        grid.addWidget(self.meta, 1, 0, 1, 7)
        card.body_layout.addLayout(grid)
        return card

    def _handle_filter_changed(self) -> None:
        self._page_index = 0
        self._refresh_table()

    def _build_table_card(self) -> QWidget:
        card = CardFrame("上游列表", "配置 URL 后可检查远程更新，一键下载到本地。")
        self.pager = Pager(show_stats=False)
        self.pager.page_requested.connect(self._set_page)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(("选择", "名称", "URL", "本地版本", "远程版本", "状态"))
        configure_table(self.table, stretch_columns=(1, 2))
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 48)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 90)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 90)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 100)
        card.body_layout.setSpacing(8)
        card.body_layout.addWidget(self.pager)
        card.body_layout.addWidget(self.table)
        return card

    def set_context(self, inventory: list[dict[str, object]], upstreams: dict[str, dict[str, object]]) -> None:
        self._inventory = deepcopy(inventory) if isinstance(inventory, list) else []
        self._upstreams = deepcopy(upstreams) if isinstance(upstreams, dict) else {}
        self._page_index = 0
        self._refresh_table()

    def set_update_results(self, results: list[dict[str, object]]) -> None:
        self._update_results = {str(item.get("name")): deepcopy(item) for item in results if isinstance(item, dict)}
        self._refresh_table()

    def set_busy(self, busy: bool) -> None:
        for button in (self.add_button, self.set_url_button, self.check_button, self.upgrade_button):
            button.set_busy(busy)

    def _filtered_rows(self) -> list[dict[str, object]]:
        query = self.search.text().strip().lower()
        rows: list[dict[str, object]] = []
        for skill in self._inventory:
            name = str(skill.get("name") or "")
            path = str(skill.get("path") or "")
            upstream = self._upstreams.get(name, {}) if isinstance(self._upstreams, dict) else {}
            url = str(upstream.get("url") or "")
            haystack = f"{name}\n{path}\n{url}".lower()
            if query and query not in haystack:
                continue
            rows.append({"name": name, "path": path, "url": url, "installedCommit": upstream.get("installedCommit")})
        return rows

    def _set_page(self, page_index: int) -> None:
        self._page_index = int(page_index)
        self._refresh_table()

    def _refresh_table(self) -> None:
        rows = self._filtered_rows()
        visible, page_index, page_count, total = paginate(rows, self._page_index, self._page_size)
        self._page_index = page_index
        self._visible_rows = visible
        self._bulk_updating = True
        try:
            self.table.setRowCount(0)
            for row in self._visible_rows:
                self._append_row(row)
        finally:
            self._bulk_updating = False
        self._sync_select_all_state()
        self.pager.set_state(self._page_index, page_count, total)
        self._update_meta(total)

    def _append_row(self, row: dict[str, object]) -> None:
        name = str(row.get("name") or "")
        url = str(row.get("url") or "").strip() or "未配置"
        installed = str(row.get("installedCommit") or "").strip() or "—"
        update = self._update_results.get(name, {})
        latest = str(update.get("latestCommit") or "").strip() or "—"
        status = str(update.get("message") or ("未配置 URL" if url == "未配置" else "未检查"))
        index = self.table.rowCount()
        self.table.insertRow(index)

        checkbox = QCheckBox()
        checkbox.setChecked(name in self._selected)
        checkbox.stateChanged.connect(lambda _state, skill=name: self._toggle_selected(skill))
        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wrapper_layout.addWidget(checkbox)
        self.table.setCellWidget(index, 0, wrapper)

        self.table.setItem(index, 1, QTableWidgetItem(name))
        url_item = QTableWidgetItem(url)
        url_item.setToolTip(str(row.get("url") or "").strip() or "")
        self.table.setItem(index, 2, url_item)
        self.table.setItem(index, 3, QTableWidgetItem(installed))
        self.table.setItem(index, 4, QTableWidgetItem(latest))
        self.table.setItem(index, 5, QTableWidgetItem(status))

    def _toggle_selected(self, name: str) -> None:
        if self._bulk_updating:
            return
        if name in self._selected:
            self._selected.remove(name)
        else:
            self._selected.add(name)
        self._sync_select_all_state()

    def _selected_names(self) -> list[str]:
        return sorted(self._selected)

    def _toggle_select_all(self, state: int) -> None:
        if self._bulk_updating:
            return
        rows = self._filtered_rows()
        visible = {str(item.get("name") or "") for item in rows}
        checked = bool(state)
        self._bulk_updating = True
        try:
            if checked:
                self._selected |= visible
            else:
                self._selected -= visible
            for row_index in range(self.table.rowCount()):
                widget = self.table.cellWidget(row_index, 0)
                cb = widget.findChild(QCheckBox) if widget else None
                if isinstance(cb, QCheckBox):
                    name_item = self.table.item(row_index, 1)
                    if name_item and name_item.text() in visible:
                        cb.setChecked(checked)
        finally:
            self._bulk_updating = False
        self._sync_select_all_state()

    def _sync_select_all_state(self) -> None:
        rows = self._filtered_rows()
        visible = {str(item.get("name") or "") for item in rows}
        if not visible:
            self.select_all.setChecked(False)
            return
        self._bulk_updating = True
        try:
            self.select_all.setChecked(bool(visible) and visible.issubset(self._selected))
        finally:
            self._bulk_updating = False

    def _update_meta(self, visible_count: int) -> None:
        self.meta.setText(f"共 {visible_count} 条 · 已选 {len(self._selected)} 条")

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
        self.add_requested.emit(payload)

    def _open_set_url_dialog(self) -> None:
        names = self._selected_names()
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
        names = self._selected_names()
        if not names:
            QMessageBox.warning(self, "检查失败", "请先选择 Skill。")
            return
        self.check_requested.emit({"names": names})

    def _emit_upgrade(self) -> None:
        names = self._selected_names()
        if not names:
            QMessageBox.warning(self, "下载失败", "请先选择 Skill。")
            return
        answer = QMessageBox.question(self, "确认下载", f"将覆盖 {len(names)} 个 Skill 的本地目录，继续吗？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.upgrade_requested.emit({"names": names})
