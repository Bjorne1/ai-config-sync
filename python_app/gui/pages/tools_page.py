from copy import deepcopy

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.tool_definitions import UPDATE_TOOL_TYPES
from ..widgets import ActionButton, CardFrame, configure_table


class UpdateToolDefinitionDialog(QDialog):
    def __init__(
        self,
        title: str,
        initial_name: str = "",
        initial_type: str = "npm",
        initial_value: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self._hint = QLabel("")
        self._hint.setObjectName("muted")
        self._hint.setWordWrap(True)
        self.name_input = QLineEdit(initial_name)
        self.type_input = QComboBox()
        self.type_input.addItems(UPDATE_TOOL_TYPES)
        self.type_input.setCurrentText(initial_type)
        self.value_input = QLineEdit(initial_value)
        self.type_input.currentTextChanged.connect(self._refresh_hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(14)
        form.addRow("名称", self.name_input)
        form.addRow("类型", self.type_input)
        form.addRow("包名 / 命令", self.value_input)
        layout.addLayout(form)
        layout.addWidget(self._hint)
        layout.addWidget(buttons)
        self._refresh_hint(self.type_input.currentText())

    def _refresh_hint(self, tool_type: str) -> None:
        hints = {
            "npm": "npm 类型填写包名，例如 `@openai/codex`。",
            "npx": "npx 类型填写完整命令，例如 `npx @openai/codex@latest`。",
            "custom": "custom 类型填写完整命令，例如 `claude update`。",
        }
        self._hint.setText(hints.get(tool_type, ""))


class ToolsPage(QWidget):
    update_requested = Signal(object)
    update_tool_requested = Signal(str, object)
    definitions_save_requested = Signal(object)

    _PAGE_SPACING = 18
    _CARD_SPACING = 18
    _TABLE_HEIGHT_BUFFER = 8
    _MAX_VISIBLE_RESULT_ROWS = 6
    _MIN_VISIBLE_DEFINITION_ROWS = 6
    _MAX_VISIBLE_DEFINITION_ROWS = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._definitions: dict[str, dict[str, str]] = {}
        self._version_selectors: dict[str, QComboBox] = {}
        self._update_buttons: dict[str, ActionButton] = {}
        self._edit_buttons: dict[str, ActionButton] = {}
        self._delete_buttons: dict[str, ActionButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._PAGE_SPACING)
        layout.addWidget(self._build_action_card())
        layout.addWidget(self._build_definition_card())
        layout.addWidget(self._build_result_card())
        layout.addStretch(1)

    def _build_action_card(self) -> QWidget:
        self.action_card = CardFrame("更新入口", "确认下方定义无误后，一键更新。")
        self.definition_meta = QLabel("正在加载…")
        self.definition_meta.setObjectName("muted")
        self.definition_meta.setWordWrap(True)
        self.run_button = ActionButton("一键更新", "primary")
        self.run_button.clicked.connect(self._emit_update_all)
        self.new_button = ActionButton("新增", "secondary")
        self.new_button.clicked.connect(self._create_definition)
        self.action_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(self._CARD_SPACING)
        row.addWidget(self.definition_meta, 1)
        row.addWidget(self.new_button, 0)
        row.addWidget(self.run_button, 0)
        self.action_card.body_layout.addLayout(row)
        return self.action_card

    def _build_definition_card(self) -> QWidget:
        self.definition_card = CardFrame("更新定义", "支持 npm / npx / 自定义命令，可单独更新、编辑或删除。")
        self.definition_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.definition_table = self._build_definition_table()
        self.definition_card.body_layout.addWidget(self.definition_table)
        return self.definition_card

    def _build_definition_table(self) -> QTableWidget:
        table = QTableWidget(0, 8)
        table.setHorizontalHeaderLabels(("名称", "类型", "包名 / 命令", "Win版本", "WSL版本", "最新版本", "目标版本", "操作"))
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        configure_table(table, stretch_columns=(2, 3, 4, 5, 6))
        return table

    def _build_result_card(self) -> QWidget:
        self.result_card = CardFrame("更新结果", "更新前后版本对比。")
        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels(("名称", "类型", "版本", "结果"))
        configure_table(self.result_table, stretch_columns=(2,))
        self.result_card.body_layout.addWidget(self.result_table)
        self.result_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._sync_result_table_height()
        return self.result_card

    def set_context(
        self,
        definitions: dict[str, dict[str, str]],
        results: list[dict[str, object]],
        statuses: dict[str, dict[str, object]],
    ) -> None:
        self._definitions = deepcopy(definitions)
        self._version_selectors = {}
        self._update_buttons = {}
        self._edit_buttons = {}
        self._delete_buttons = {}
        entries = sorted(definitions.items(), key=lambda item: item[0].lower())
        self.definition_meta.setText(f"共 {len(entries)} 个更新定义（npm / npx / custom）")
        self.definition_table.setRowCount(len(entries))
        for row_index, (name, definition) in enumerate(entries):
            win_text, wsl_text, latest_text, recent_versions = self._definition_versions(name, definition, statuses)
            for column, value in enumerate(
                (name, definition["type"], self._definition_value(definition), win_text, wsl_text, latest_text)
            ):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.definition_table.setItem(row_index, column, item)
            self.definition_table.setCellWidget(
                row_index,
                6,
                self._build_target_version_cell(name, definition, latest_text, recent_versions),
            )
            self.definition_table.setCellWidget(row_index, 7, self._build_operation_cell(name))
        self._sync_definition_table_height()
        self.result_table.setRowCount(len(results))
        for row_index, result in enumerate(results):
            version = self._result_versions(result)
            status = self._result_status(result)
            values = (result["name"], result["type"], version, status)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.result_table.setItem(row_index, column, item)
        self._sync_result_table_height()

    def set_busy(self, batch_busy: bool, save_busy: bool, busy_tools: set[str] = frozenset()) -> None:
        self.run_button.set_busy(batch_busy)
        self.new_button.setDisabled(batch_busy or save_busy)
        disable_all = batch_busy or save_busy
        for name, selector in self._version_selectors.items():
            selector.setDisabled(disable_all or name in busy_tools)
        for name, button in self._update_buttons.items():
            if name in busy_tools:
                button.set_busy(True)
            else:
                button.set_busy(False)
                button.setDisabled(disable_all)
        for name, button in self._edit_buttons.items():
            button.setDisabled(disable_all or name in busy_tools)
        for name, button in self._delete_buttons.items():
            button.setDisabled(disable_all or name in busy_tools)
        self.definition_table.setDisabled(save_busy)

    def _definition_value(self, definition: dict[str, str]) -> str:
        return definition.get("package") or definition.get("command") or ""

    def _build_operation_cell(self, name: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        update_button = ActionButton("更新", "secondary")
        edit_button = ActionButton("编辑", "secondary")
        delete_button = ActionButton("删除", "danger")
        update_button.clicked.connect(
            lambda _checked=False, tool_name=name: self.update_tool_requested.emit(
                tool_name,
                self._selected_version_for(tool_name),
            )
        )
        edit_button.clicked.connect(lambda _checked=False, tool_name=name: self._edit_definition(tool_name))
        delete_button.clicked.connect(lambda _checked=False, tool_name=name: self._delete_definition(tool_name))
        layout.addWidget(update_button)
        layout.addWidget(edit_button)
        layout.addWidget(delete_button)
        self._update_buttons[name] = update_button
        self._edit_buttons[name] = edit_button
        self._delete_buttons[name] = delete_button
        return container

    def _definition_versions(
        self,
        name: str,
        definition: dict[str, str],
        statuses: dict[str, dict[str, object]],
    ) -> tuple[str, str, str, list[str]]:
        if definition.get("type") != "npm":
            return ("n/a", "n/a", "n/a", [])
        status = statuses.get(name, {})
        wsl_enabled = bool(status.get("wslEnabled"))
        windows_version = str(status.get("currentWindows") or "n/a")
        wsl_version = str(status.get("currentWsl") or "n/a") if wsl_enabled else "n/a"
        latest_version = str(status.get("latest") or "n/a")
        raw_recent = status.get("recentVersions")
        recent_versions = []
        if isinstance(raw_recent, list):
            recent_versions = [str(item).strip() for item in raw_recent if str(item).strip()]
        return (windows_version, wsl_version, latest_version, recent_versions)

    def _build_target_version_cell(
        self,
        name: str,
        definition: dict[str, str],
        latest_version: str,
        recent_versions: list[str],
    ) -> QWidget:
        if definition.get("type") != "npm":
            return QLabel("n/a")
        combo = QComboBox()
        candidates: list[str] = []
        if latest_version and latest_version != "n/a":
            candidates.append(latest_version)
        candidates.extend(recent_versions)
        deduped: list[str] = []
        seen: set[str] = set()
        for version in candidates:
            if version in seen:
                continue
            seen.add(version)
            deduped.append(version)
        if not deduped:
            deduped = ["latest"]
        for version in deduped:
            combo.addItem(version, version)
        self._version_selectors[name] = combo
        return combo

    def _selected_version_for(self, name: str) -> str | None:
        selector = self._version_selectors.get(name)
        if selector is None:
            return None
        version = str(selector.currentData() or selector.currentText() or "").strip()
        return version or None

    def _collect_target_versions(self) -> dict[str, str]:
        versions: dict[str, str] = {}
        for name, definition in self._definitions.items():
            if definition.get("type") != "npm":
                continue
            selected = self._selected_version_for(name)
            if selected:
                versions[name] = selected
        return versions

    def _emit_update_all(self) -> None:
        self.update_requested.emit(self._collect_target_versions())

    def _result_versions(self, result: dict[str, object]) -> str:
        windows = f"{result.get('versionBefore') or 'n/a'} -> {result.get('versionAfter') or 'n/a'}"
        if result.get("successWsl") is None:
            return windows
        wsl = f"{result.get('wslVersionBefore') or 'n/a'} -> {result.get('wslVersionAfter') or 'n/a'}"
        return f"Win {windows} / WSL {wsl}"

    def _result_status(self, result: dict[str, object]) -> str:
        if result.get("successWsl") is None:
            return "成功" if result.get("success") else "失败"
        win = "成功" if result.get("successWindows") else "失败"
        wsl = "成功" if result.get("successWsl") else "失败"
        return f"Win {win} / WSL {wsl}"

    def _create_definition(self) -> None:
        self._open_definition_dialog("新增定义")

    def _edit_definition(self, name: str) -> None:
        if name not in self._definitions:
            QMessageBox.warning(self, "编辑失败", f"找不到定义：{name}")
            return
        definition = self._definitions[name]
        self._open_definition_dialog(
            "编辑定义",
            initial_name=name,
            initial_type=definition.get("type", "npm"),
            initial_value=self._definition_value(definition),
            original_name=name,
        )

    def _open_definition_dialog(
        self,
        title: str,
        initial_name: str = "",
        initial_type: str = "npm",
        initial_value: str = "",
        original_name: str | None = None,
    ) -> None:
        dialog = UpdateToolDefinitionDialog(
            title,
            initial_name=initial_name,
            initial_type=initial_type,
            initial_value=initial_value,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name = dialog.name_input.text().strip()
        tool_type = dialog.type_input.currentText()
        value = dialog.value_input.text().strip()
        if not name:
            QMessageBox.warning(self, "保存失败", "请填写名称。")
            return
        if not value:
            QMessageBox.warning(self, "保存失败", "请填写包名或命令。")
            return
        definition = {"type": tool_type, "package": value} if tool_type == "npm" else {"type": tool_type, "command": value}
        next_definitions = deepcopy(self._definitions)
        if original_name and original_name != name:
            next_definitions.pop(original_name, None)
        next_definitions[name] = definition
        self.definitions_save_requested.emit(next_definitions)

    def _delete_definition(self, name: str) -> None:
        if name not in self._definitions:
            QMessageBox.warning(self, "删除失败", f"找不到定义：{name}")
            return
        answer = QMessageBox.question(self, "确认删除", f'确定要删除「{name}」吗？')
        if answer != QMessageBox.StandardButton.Yes:
            return
        next_definitions = deepcopy(self._definitions)
        next_definitions.pop(name, None)
        self.definitions_save_requested.emit(next_definitions)

    def _sync_definition_table_height(self) -> None:
        row_count = self.definition_table.rowCount()
        visible_rows = min(
            max(row_count, self._MIN_VISIBLE_DEFINITION_ROWS),
            self._MAX_VISIBLE_DEFINITION_ROWS,
        )
        self.definition_table.setFixedHeight(self._table_height(self.definition_table, visible_rows))

    def _sync_result_table_height(self) -> None:
        visible_rows = min(self.result_table.rowCount(), self._MAX_VISIBLE_RESULT_ROWS)
        self.result_table.setFixedHeight(self._table_height(self.result_table, visible_rows))

    def _table_height(self, table: QTableWidget, rows: int) -> int:
        header_height = table.horizontalHeader().sizeHint().height()
        row_height = table.verticalHeader().defaultSectionSize()
        frame_height = table.frameWidth() * 2
        return frame_height + header_height + (rows * row_height) + self._TABLE_HEIGHT_BUFFER
