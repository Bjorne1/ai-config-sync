from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ..widgets import ActionButton, CardFrame, HeaderBlock, configure_table, layout_container


class ToolsPage(QWidget):
    update_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(HeaderBlock("07 / Tools", "工具更新", "配置中的更新定义和最近更新结果分层展示。"))
        layout.addWidget(self._build_top_row())
        layout.addWidget(self._build_result_card(), 1)

    def _build_top_row(self) -> QWidget:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.addWidget(self._build_action_card(), 0, 0)
        grid.addWidget(self._build_definition_card(), 0, 1)
        return layout_container(grid)

    def _build_action_card(self) -> QWidget:
        self.action_card = CardFrame("更新入口", "先看定义总数，再执行一键更新。")
        self.definition_meta = QLabel("等待配置回填。")
        self.definition_meta.setObjectName("muted")
        self.definition_meta.setWordWrap(True)
        self.run_button = ActionButton("一键更新工具", "primary")
        self.run_button.clicked.connect(self.update_requested.emit)
        self.action_card.body_layout.addWidget(self.definition_meta)
        self.action_card.body_layout.addWidget(self.run_button)
        return self.action_card

    def _build_definition_card(self) -> QWidget:
        self.definition_card = CardFrame("更新定义", "当前配置里的包更新和自定义命令。")
        self.definition_table = QTableWidget(0, 3)
        self.definition_table.setHorizontalHeaderLabels(("名称", "类型", "命令 / 包"))
        configure_table(self.definition_table, stretch_columns=(2,))
        self.definition_table.setMaximumHeight(220)
        self.definition_card.body_layout.addWidget(self.definition_table)
        return self.definition_card

    def _build_result_card(self) -> QWidget:
        self.result_card = CardFrame("最近更新结果", "对比更新前后版本并标记执行结果。")
        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels(("名称", "类型", "版本", "结果"))
        configure_table(self.result_table, stretch_columns=(2,))
        self.result_card.body_layout.addWidget(self.result_table)
        return self.result_card

    def set_context(self, definitions: dict[str, dict[str, str]], results: list[dict[str, object]]) -> None:
        entries = list(definitions.items())
        self.definition_meta.setText(f"已定义 {len(entries)} 个更新动作。")
        self.definition_table.setRowCount(len(entries))
        for row_index, (name, definition) in enumerate(entries):
            command = definition.get("package") or definition.get("command") or ""
            for column, value in enumerate((name, definition["type"], command)):
                self.definition_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.result_table.setRowCount(len(results))
        for row_index, result in enumerate(results):
            version = f"{result.get('versionBefore') or 'n/a'} -> {result.get('versionAfter') or 'n/a'}"
            status = "成功" if result.get("success") else "失败"
            values = (result["name"], result["type"], version, status)
            for column, value in enumerate(values):
                self.result_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def set_busy(self, busy: bool) -> None:
        self.run_button.set_busy(busy)
