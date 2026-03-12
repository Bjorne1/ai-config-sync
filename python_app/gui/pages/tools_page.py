from copy import deepcopy

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
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


class ToolsPage(QWidget):
    update_requested = Signal()
    definitions_save_requested = Signal(object)

    _PAGE_SPACING = 12
    _CARD_SPACING = 16
    _DEFINITION_PANEL_SPACING = 16
    _TABLE_HEIGHT_BUFFER = 8
    _MAX_VISIBLE_RESULT_ROWS = 6
    _MIN_VISIBLE_DEFINITION_ROWS = 6
    _MAX_VISIBLE_DEFINITION_ROWS = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._definitions: dict[str, dict[str, str]] = {}
        self._editing_name: str | None = None
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
        self.action_card = CardFrame("更新入口", "先确认定义，再执行一键更新。")
        self.definition_meta = QLabel("等待配置回填。")
        self.definition_meta.setObjectName("muted")
        self.definition_meta.setWordWrap(True)
        self.run_button = ActionButton("一键更新工具", "primary")
        self.run_button.clicked.connect(self.update_requested.emit)
        self.action_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(self._CARD_SPACING)
        row.addWidget(self.definition_meta, 1)
        row.addWidget(self.run_button, 0)
        self.action_card.body_layout.addLayout(row)
        return self.action_card

    def _build_definition_card(self) -> QWidget:
        self.definition_card = CardFrame("更新定义", "支持 npm、npx 和自定义命令，选中表格即可编辑。")
        self.definition_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.definition_table = self._build_definition_table()
        editor = self._build_definition_editor()
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(self._DEFINITION_PANEL_SPACING)
        body.addWidget(self.definition_table, 7)
        body.addWidget(editor, 5)
        self.definition_card.body_layout.addLayout(body)
        self._refresh_editor_hint(self.type_input.currentText())
        return self.definition_card

    def _build_definition_table(self) -> QTableWidget:
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(("名称", "类型", "包名 / 命令"))
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.itemSelectionChanged.connect(self._load_selected_definition)
        configure_table(table, stretch_columns=(2,))
        return table

    def _build_definition_editor(self) -> QWidget:
        editor = QWidget()
        layout = QVBoxLayout(editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        self.name_input = QLineEdit()
        self.type_input = QComboBox()
        self.type_input.addItems(UPDATE_TOOL_TYPES)
        self.type_input.currentTextChanged.connect(self._refresh_editor_hint)
        self.value_input = QLineEdit()
        form.addRow("名称", self.name_input)
        form.addRow("类型", self.type_input)
        form.addRow("包名 / 命令", self.value_input)
        layout.addLayout(form)

        self.editor_hint = QLabel("")
        self.editor_hint.setObjectName("muted")
        self.editor_hint.setWordWrap(True)
        layout.addWidget(self.editor_hint)

        self.editor_status = QLabel("新增模式：填写定义后点击“保存定义”。")
        self.editor_status.setObjectName("muted")
        self.editor_status.setWordWrap(True)
        layout.addWidget(self.editor_status)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(10)
        self.new_button = ActionButton("新增", "secondary")
        self.save_button = ActionButton("保存定义", "primary")
        self.delete_button = ActionButton("删除选中", "danger")
        self.reset_button = ActionButton("清空输入", "secondary")
        self.new_button.clicked.connect(self._start_new_definition)
        self.save_button.clicked.connect(self._save_definition)
        self.delete_button.clicked.connect(self._delete_definition)
        self.reset_button.clicked.connect(self._clear_editor)
        for button in (self.new_button, self.save_button, self.delete_button, self.reset_button):
            button_row.addWidget(button)
        layout.addLayout(button_row)
        layout.addStretch(1)
        return editor

    def _build_result_card(self) -> QWidget:
        self.result_card = CardFrame("最近更新结果", "对比更新前后版本并标记执行结果。")
        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels(("名称", "类型", "版本", "结果"))
        configure_table(self.result_table, stretch_columns=(2,))
        self.result_card.body_layout.addWidget(self.result_table)
        self.result_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._sync_result_table_height()
        return self.result_card

    def set_context(self, definitions: dict[str, dict[str, str]], results: list[dict[str, object]]) -> None:
        self._definitions = deepcopy(definitions)
        entries = sorted(definitions.items(), key=lambda item: item[0].lower())
        self.definition_meta.setText(f"已定义 {len(entries)} 个更新动作，支持 npm / npx / custom。")
        self.definition_table.setRowCount(len(entries))
        for row_index, (name, definition) in enumerate(entries):
            for column, value in enumerate((name, definition["type"], self._definition_value(definition))):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.definition_table.setItem(row_index, column, item)
        self._sync_definition_table_height()
        if self._editing_name and self._editing_name in self._definitions:
            self._select_definition(self._editing_name)
        elif entries and not self.definition_table.selectedItems():
            self._select_definition(entries[0][0])
        elif not entries:
            self._clear_editor(clear_selection=False)
        self.result_table.setRowCount(len(results))
        for row_index, result in enumerate(results):
            version = f"{result.get('versionBefore') or 'n/a'} -> {result.get('versionAfter') or 'n/a'}"
            status = "成功" if result.get("success") else "失败"
            values = (result["name"], result["type"], version, status)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.result_table.setItem(row_index, column, item)
        self._sync_result_table_height()

    def set_busy(self, update_busy: bool, save_busy: bool) -> None:
        self.run_button.set_busy(update_busy)
        self.save_button.set_busy(save_busy)
        for widget in (
            self.new_button,
            self.delete_button,
            self.reset_button,
            self.name_input,
            self.type_input,
            self.value_input,
            self.definition_table,
        ):
            widget.setDisabled(save_busy)

    def _definition_value(self, definition: dict[str, str]) -> str:
        return definition.get("package") or definition.get("command") or ""

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

    def _refresh_editor_hint(self, tool_type: str) -> None:
        hints = {
            "npm": "npm 类型填写包名，例如 `@openai/codex`。",
            "npx": "npx 类型填写完整命令，例如 `npx @openai/codex@latest`。",
            "custom": "custom 类型填写完整命令，例如 `claude update`。",
        }
        self.editor_hint.setText(hints.get(tool_type, ""))

    def _selected_definition_name(self) -> str | None:
        items = self.definition_table.selectedItems()
        if not items:
            return None
        row = items[0].row()
        name_item = self.definition_table.item(row, 0)
        return name_item.text().strip() if name_item else None

    def _select_definition(self, name: str) -> None:
        for row in range(self.definition_table.rowCount()):
            item = self.definition_table.item(row, 0)
            if item and item.text() == name:
                self.definition_table.selectRow(row)
                return

    def _load_selected_definition(self) -> None:
        name = self._selected_definition_name()
        if not name or name not in self._definitions:
            return
        definition = self._definitions[name]
        self._editing_name = name
        self.name_input.setText(name)
        self.type_input.setCurrentText(definition["type"])
        self.value_input.setText(self._definition_value(definition))
        self.editor_status.setText(f"编辑模式：{name}")

    def _start_new_definition(self) -> None:
        self._clear_editor()
        self.editor_status.setText("新增模式：填写定义后点击“保存定义”。")

    def _clear_editor(self, clear_selection: bool = True) -> None:
        self._editing_name = None
        if clear_selection:
            self.definition_table.clearSelection()
        self.name_input.clear()
        self.type_input.setCurrentText("npm")
        self.value_input.clear()
        self.editor_status.setText("新增模式：填写定义后点击“保存定义”。")

    def _save_definition(self) -> None:
        name = self.name_input.text().strip()
        tool_type = self.type_input.currentText()
        value = self.value_input.text().strip()
        if not name:
            self.editor_status.setText("保存失败：请先填写名称。")
            return
        if not value:
            self.editor_status.setText("保存失败：请先填写包名或命令。")
            return
        definition = {"type": tool_type, "package": value} if tool_type == "npm" else {"type": tool_type, "command": value}
        next_definitions = deepcopy(self._definitions)
        if self._editing_name and self._editing_name != name:
            next_definitions.pop(self._editing_name, None)
        next_definitions[name] = definition
        self._editing_name = name
        self.editor_status.setText(f"已提交保存：{name}")
        self.definitions_save_requested.emit(next_definitions)

    def _delete_definition(self) -> None:
        name = self._editing_name or self._selected_definition_name()
        if not name or name not in self._definitions:
            self.editor_status.setText("删除失败：请先选择一条更新定义。")
            return
        answer = QMessageBox.question(self, "删除更新定义", f"确认删除 “{name}” 吗？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        next_definitions = deepcopy(self._definitions)
        next_definitions.pop(name, None)
        self._editing_name = None
        self.editor_status.setText(f"已提交删除：{name}")
        self.definitions_save_requested.emit(next_definitions)
