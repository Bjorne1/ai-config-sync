from copy import deepcopy
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ...core.tool_definitions import ENVIRONMENT_IDS, GLOBAL_RULE_TOOL_IDS
from ..dashboard import serialize
from ..widgets import ActionButton, BadgeLabel, CardFrame

ENVIRONMENT_LABELS = {"windows": "Windows", "wsl": "WSL"}
TOOL_LABELS = {"claude": "Claude", "codex": "Codex", "gemini": "Gemini"}
STATE_LABELS = {
    "idle": "未分配",
    "healthy": "已同步",
    "outdated": "待同步",
    "drifted": "目标漂移",
    "tool_unavailable": "工具不可用",
    "environment_error": "环境异常",
    "profile_missing": "规则缺失",
}


class GlobalRuleEditDialog(QDialog):

    def __init__(
        self,
        name: str = "",
        content: str = "",
        title: str = "新建规则",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 480)
        self.resize(720, 560)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        name_label = QLabel("规则名称")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入规则名称")
        self.name_input.setText(name)
        content_label = QLabel("规则内容（Markdown 纯文本）")
        self.content_editor = QPlainTextEdit()
        self.content_editor.setPlaceholderText("请输入规则内容…")
        self.content_editor.setPlainText(content)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(content_label)
        layout.addWidget(self.content_editor, 1)
        layout.addWidget(self.button_box)

    def _validate_and_accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "验证失败", "规则名称不能为空。")
            return
        self.accept()

    def get_name(self) -> str:
        return self.name_input.text().strip()

    def get_content(self) -> str:
        return self.content_editor.toPlainText()


class GlobalRuleTargetCard(CardFrame):
    assignment_changed = Signal(str, str, object)
    sync_requested = Signal(str, str)

    def __init__(self, environment_id: str, tool_id: str, parent: QWidget | None = None) -> None:
        title = f"{ENVIRONMENT_LABELS[environment_id]} / {TOOL_LABELS[tool_id]}"
        super().__init__(title, "自动识别目标文件路径与同步状态。", parent)
        self.environment_id = environment_id
        self.tool_id = tool_id
        self._updating = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.batch_checkbox = QCheckBox("加入批量同步")
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._emit_assignment_changed)
        self.path_label = QLabel("--")
        self.path_label.setWordWrap(True)
        self.path_label.setObjectName("muted")
        self.status_badge = BadgeLabel("未分配", "idle")
        self.message_label = QLabel("--")
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName("muted")
        self.sync_button = ActionButton("同步此目标", "secondary")
        self.sync_button.clicked.connect(
            lambda: self.sync_requested.emit(self.environment_id, self.tool_id)
        )
        self.body_layout.addWidget(self.batch_checkbox)
        self.body_layout.addWidget(self.profile_combo)
        self.body_layout.addWidget(self.status_badge)
        self.body_layout.addWidget(self.path_label)
        self.body_layout.addWidget(self.message_label)
        self.body_layout.addWidget(self.sync_button)

    def set_context(
        self,
        profiles: list[dict[str, object]],
        status: dict[str, object],
        selected_profile_id: str | None,
        sync_enabled: bool,
    ) -> None:
        self._updating = True
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("未分配", None)
        for profile in profiles:
            self.profile_combo.addItem(
                str(profile.get("name") or "(未命名规则)"),
                str(profile["id"]),
            )
        combo_index = self.profile_combo.findData(selected_profile_id)
        self.profile_combo.setCurrentIndex(combo_index if combo_index >= 0 else 0)
        self.profile_combo.blockSignals(False)
        self._updating = False
        state = str(status.get("state") or "idle")
        self.status_badge.setText(STATE_LABELS.get(state, state))
        self.status_badge.set_state(state)
        target_path = str(status.get("targetFilePath") or "未识别到目标文件")
        self.path_label.setText(target_path)
        self.path_label.setToolTip(target_path)
        message = str(status.get("message") or "--")
        self.message_label.setText(message)
        self.message_label.setToolTip(message)
        can_sync = sync_enabled and bool(selected_profile_id)
        self.sync_button.setDisabled(not can_sync)

    def set_busy(self, busy: bool) -> None:
        self.profile_combo.setDisabled(busy)
        self.batch_checkbox.setDisabled(busy)
        self.sync_button.set_busy(busy)

    def is_checked(self) -> bool:
        return self.batch_checkbox.isChecked()

    def set_checked(self, checked: bool) -> None:
        self.batch_checkbox.setChecked(checked)

    def _emit_assignment_changed(self) -> None:
        if self._updating:
            return
        self.assignment_changed.emit(
            self.environment_id,
            self.tool_id,
            self.profile_combo.currentData(),
        )


class GlobalRulePage(QWidget):
    refresh_requested = Signal()
    save_profiles_requested = Signal(object)
    save_assignments_requested = Signal(object)
    sync_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profiles: list[dict[str, object]] = []
        self._original_profiles: list[dict[str, object]] = []
        self._assignments: dict[str, dict[str, str | None]] = {}
        self._original_assignments: dict[str, dict[str, str | None]] = {}
        self._statuses: dict[tuple[str, str], dict[str, object]] = {}
        self._selected_profile_id: str | None = None
        self._is_busy: bool = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(self._build_toolbar_card())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_profile_list_card())
        splitter.addWidget(self._build_assignment_card())
        splitter.setSizes([300, 900])
        layout.addWidget(splitter, 1)

    def _build_toolbar_card(self) -> QWidget:
        card = CardFrame("全局规则", "管理规则版本、目标映射与手动同步。")
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self.status_label = QLabel("正在加载…")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        self.refresh_button = ActionButton("刷新路径", "secondary")
        self.save_assignments_button = ActionButton("保存映射", "secondary")
        self.sync_selected_button = ActionButton("同步选中", "secondary")
        self.sync_all_button = ActionButton("同步全部", "primary")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.save_assignments_button.clicked.connect(
            lambda: self.save_assignments_requested.emit(deepcopy(self._assignments))
        )
        self.sync_selected_button.clicked.connect(self._emit_sync_selected)
        self.sync_all_button.clicked.connect(lambda: self.sync_requested.emit(None))
        row.addWidget(self.status_label, 1)
        row.addWidget(self.refresh_button)
        row.addWidget(self.save_assignments_button)
        row.addWidget(self.sync_selected_button)
        row.addWidget(self.sync_all_button)
        card.body_layout.addLayout(row)
        return card

    def _build_profile_list_card(self) -> QWidget:
        card = CardFrame("规则版本", "新建、编辑、复制或删除规则版本。")
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        self.new_button = ActionButton("新建", "secondary")
        self.edit_button = ActionButton("编辑", "secondary")
        self.copy_button = ActionButton("复制", "secondary")
        self.delete_button = ActionButton("删除", "danger")
        self.new_button.clicked.connect(self._create_profile)
        self.edit_button.clicked.connect(self._edit_profile)
        self.copy_button.clicked.connect(self._copy_profile)
        self.delete_button.clicked.connect(self._delete_profile)
        toolbar.addWidget(self.new_button)
        toolbar.addWidget(self.edit_button)
        toolbar.addWidget(self.copy_button)
        toolbar.addWidget(self.delete_button)
        card.body_layout.addLayout(toolbar)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索规则版本")
        self.search_input.textChanged.connect(self._refresh_profile_list)
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._handle_profile_selection_changed)
        self.profile_list.itemDoubleClicked.connect(lambda _item: self._edit_profile())
        card.body_layout.addWidget(self.search_input)
        card.body_layout.addWidget(self.profile_list, 1)
        return card

    def _build_assignment_card(self) -> QWidget:
        card = CardFrame("目标映射与状态", "为每个目标选择规则版本，并按目标或批量同步。")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        self._target_cards: dict[tuple[str, str], GlobalRuleTargetCard] = {}
        for index, (environment_id, tool_id) in enumerate(
            (("windows", "claude"), ("windows", "codex"), ("windows", "gemini"),
             ("wsl", "claude"), ("wsl", "codex"), ("wsl", "gemini")),
            start=0,
        ):
            card_widget = GlobalRuleTargetCard(environment_id, tool_id)
            card_widget.assignment_changed.connect(self._handle_assignment_changed)
            card_widget.sync_requested.connect(self._emit_sync_one)
            row = index // 2
            column = index % 2
            grid.addWidget(card_widget, row, column)
            self._target_cards[(environment_id, tool_id)] = card_widget
        card.body_layout.addLayout(grid)
        self.assignment_meta = QLabel("--")
        self.assignment_meta.setObjectName("muted")
        self.assignment_meta.setWordWrap(True)
        card.body_layout.addWidget(self.assignment_meta)
        return card

    def set_context(
        self,
        global_rules: dict[str, object],
        statuses: list[dict[str, object]],
    ) -> None:
        self._original_profiles = deepcopy(global_rules.get("profiles", []))
        self._profiles = deepcopy(self._original_profiles)
        self._original_assignments = deepcopy(global_rules.get("assignments", {}))
        self._assignments = deepcopy(self._original_assignments)
        self._statuses = {
            (item["environmentId"], item["toolId"]): deepcopy(item)
            for item in statuses
        }
        selected_profile_id = self._selected_profile_id
        if selected_profile_id not in {profile["id"] for profile in self._profiles}:
            selected_profile_id = self._profiles[0]["id"] if self._profiles else None
        self._selected_profile_id = selected_profile_id
        self._refresh_profile_list()
        self._select_profile(selected_profile_id)
        self._refresh_target_cards()
        self._refresh_dirty_state()

    def set_busy(
        self,
        refresh_busy: bool,
        profiles_busy: bool,
        assignments_busy: bool,
        sync_busy: bool,
    ) -> None:
        self._is_busy = refresh_busy or profiles_busy or assignments_busy or sync_busy
        self.refresh_button.set_busy(refresh_busy)
        self.save_assignments_button.set_busy(assignments_busy)
        self.sync_selected_button.set_busy(sync_busy)
        self.sync_all_button.set_busy(sync_busy)
        self.new_button.setDisabled(self._is_busy)
        self.edit_button.setDisabled(self._is_busy)
        self.copy_button.setDisabled(self._is_busy)
        self.delete_button.setDisabled(self._is_busy)
        self.search_input.setDisabled(self._is_busy)
        self.profile_list.setDisabled(self._is_busy)
        for card in self._target_cards.values():
            card.set_busy(self._is_busy)
        self._refresh_dirty_state()

    def _refresh_profile_list(self) -> None:
        query = self.search_input.text().strip().lower()
        self.profile_list.blockSignals(True)
        self.profile_list.clear()
        for profile in self._profiles:
            name = str(profile.get("name") or "(未命名规则)")
            if query and query not in name.lower():
                continue
            used_count = self._usage_count(str(profile["id"]))
            text = name if not used_count else f"{name}  ·  {used_count} 个目标"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, str(profile["id"]))
            updated_at = str(profile.get("updatedAt") or "未保存")
            item.setToolTip(f"{name}\n更新时间：{updated_at}")
            self.profile_list.addItem(item)
        self.profile_list.blockSignals(False)

    def _select_profile(self, profile_id: str | None) -> None:
        if not profile_id:
            self.profile_list.clearSelection()
            return
        for index in range(self.profile_list.count()):
            item = self.profile_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == profile_id:
                self.profile_list.setCurrentItem(item)
                return

    def _handle_profile_selection_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        self._selected_profile_id = current.data(Qt.ItemDataRole.UserRole) if current else None

    def _create_profile(self) -> None:
        dialog = GlobalRuleEditDialog(title="新建规则", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        profile_id = uuid4().hex
        self._profiles.append(
            {
                "id": profile_id,
                "name": dialog.get_name(),
                "file": f"{profile_id}.md",
                "updatedAt": "",
                "content": dialog.get_content(),
            }
        )
        self._selected_profile_id = profile_id
        self._emit_save_profiles()

    def _edit_profile(self) -> None:
        profile = self._current_profile()
        if not profile:
            QMessageBox.warning(self, "编辑失败", "请先选择一个规则版本。")
            return
        dialog = GlobalRuleEditDialog(
            name=str(profile.get("name") or ""),
            content=str(profile.get("content") or ""),
            title="编辑规则",
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        profile["name"] = dialog.get_name()
        profile["content"] = dialog.get_content()
        self._emit_save_profiles()

    def _copy_profile(self) -> None:
        profile = self._current_profile()
        if not profile:
            QMessageBox.warning(self, "复制失败", "请先选择一个规则版本。")
            return
        dialog = GlobalRuleEditDialog(
            name=f"{profile.get('name') or '未命名规则'} 副本",
            content=str(profile.get("content") or ""),
            title="复制规则",
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        profile_id = uuid4().hex
        self._profiles.append(
            {
                "id": profile_id,
                "name": dialog.get_name(),
                "file": f"{profile_id}.md",
                "updatedAt": "",
                "content": dialog.get_content(),
            }
        )
        self._selected_profile_id = profile_id
        self._emit_save_profiles()

    def _delete_profile(self) -> None:
        profile = self._current_profile()
        if not profile:
            QMessageBox.warning(self, "删除失败", "请先选择一个规则版本。")
            return
        profile_id = str(profile["id"])
        if self._usage_count(profile_id):
            QMessageBox.warning(self, "删除失败", "该规则版本仍被目标映射引用，请先解除映射。")
            return
        answer = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除规则「{profile.get('name')}」吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._profiles = [
            item for item in self._profiles if str(item["id"]) != profile_id
        ]
        self._selected_profile_id = self._profiles[0]["id"] if self._profiles else None
        self._emit_save_profiles()

    def _emit_save_profiles(self) -> None:
        payload = {
            "profiles": [
                {
                    "id": str(profile["id"]),
                    "name": str(profile.get("name") or ""),
                    "content": str(profile.get("content") or ""),
                    "updatedAt": str(profile.get("updatedAt") or ""),
                }
                for profile in self._profiles
            ]
        }
        self.save_profiles_requested.emit(payload)

    def _handle_assignment_changed(
        self,
        environment_id: str,
        tool_id: str,
        profile_id: object,
    ) -> None:
        self._assignments[environment_id][tool_id] = str(profile_id) if profile_id else None
        self._refresh_target_cards()
        self._refresh_dirty_state()

    def _emit_sync_one(self, environment_id: str, tool_id: str) -> None:
        self.sync_requested.emit([{"environmentId": environment_id, "toolId": tool_id}])

    def _emit_sync_selected(self) -> None:
        targets = []
        for (environment_id, tool_id), card in self._target_cards.items():
            if card.is_checked():
                targets.append({"environmentId": environment_id, "toolId": tool_id})
        if not targets:
            QMessageBox.warning(self, "同步失败", "请先勾选至少一个目标。")
            return
        self.sync_requested.emit(targets)

    def _refresh_target_cards(self) -> None:
        sync_enabled = not self._assignments_dirty()
        for environment_id in ENVIRONMENT_IDS:
            for tool_id in GLOBAL_RULE_TOOL_IDS:
                profile_id = self._assignments[environment_id][tool_id]
                status = self._display_status(environment_id, tool_id)
                self._target_cards[(environment_id, tool_id)].set_context(
                    self._profiles,
                    status,
                    profile_id,
                    sync_enabled,
                )

    def _display_status(self, environment_id: str, tool_id: str) -> dict[str, object]:
        status = deepcopy(self._statuses.get((environment_id, tool_id), {}))
        profile_id = self._assignments[environment_id][tool_id]
        profile = self._profile_by_id(profile_id)
        status["profileId"] = profile_id
        status["profileName"] = profile.get("name") if profile else None
        if status.get("state") in {"environment_error", "tool_unavailable"}:
            return status
        if not profile_id:
            return {
                **status,
                "state": "idle",
                "message": "未分配规则版本",
            }
        if not profile:
            return {
                **status,
                "state": "profile_missing",
                "message": f"规则版本不存在：{profile_id}",
            }
        original_profile_id = self._original_assignments.get(environment_id, {}).get(tool_id)
        if profile_id != original_profile_id:
            return {
                **status,
                "state": "outdated",
                "message": "目标映射已修改，保存后可同步",
            }
        return status or {
            "environmentId": environment_id,
            "toolId": tool_id,
            "targetFilePath": None,
            "profileId": profile_id,
            "profileName": profile.get("name"),
            "state": "outdated",
            "message": "等待状态刷新",
        }

    def _refresh_dirty_state(self) -> None:
        assignments_dirty = self._assignments_dirty()
        referenced = sum(
            1
            for environment_id in ENVIRONMENT_IDS
            for tool_id in GLOBAL_RULE_TOOL_IDS
            if self._assignments.get(environment_id, {}).get(tool_id)
        )
        sync_message = "映射有未保存修改" if assignments_dirty else "可直接同步"
        self.status_label.setText(
            f"规则版本 {len(self._profiles)} 个 · 已分配目标 {referenced} 个 · {sync_message}"
        )
        self.assignment_meta.setText(
            "映射已保存" if not assignments_dirty else "映射有未保存修改，请先保存映射。"
        )
        if not self._is_busy:
            self.save_assignments_button.setDisabled(not assignments_dirty)
            self.sync_selected_button.setDisabled(assignments_dirty)
            self.sync_all_button.setDisabled(assignments_dirty)

    def _assignments_dirty(self) -> bool:
        return serialize(self._assignments) != serialize(self._original_assignments)

    def _current_profile(self) -> dict[str, object] | None:
        return self._profile_by_id(self._selected_profile_id)

    def _profile_by_id(self, profile_id: str | None) -> dict[str, object] | None:
        if not profile_id:
            return None
        return next(
            (profile for profile in self._profiles if str(profile["id"]) == str(profile_id)),
            None,
        )

    def _usage_count(self, profile_id: str) -> int:
        return sum(
            1
            for environment_id in ENVIRONMENT_IDS
            for tool_id in GLOBAL_RULE_TOOL_IDS
            if self._assignments.get(environment_id, {}).get(tool_id) == profile_id
        )
