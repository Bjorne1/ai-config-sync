from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ..widgets import ActionButton, CardFrame, HeaderBlock


class ToolsPage(QWidget):
    update_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(HeaderBlock("07 / Tools", "工具更新", "配置中的更新定义和最近更新结果并排展示。"))
        self.definition_card = CardFrame("更新定义")
        self.definition_table = QTableWidget(0, 3)
        self.definition_table.setHorizontalHeaderLabels(("名称", "类型", "命令 / 包"))
        self.definition_table.verticalHeader().setVisible(False)
        self.definition_card.body_layout.addWidget(self.definition_table)
        layout.addWidget(self.definition_card)
        self.result_card = CardFrame("最近更新结果")
        self.run_button = ActionButton("一键更新工具", "primary")
        self.run_button.clicked.connect(self.update_requested.emit)
        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels(("名称", "类型", "版本", "结果"))
        self.result_table.verticalHeader().setVisible(False)
        self.result_card.body_layout.addWidget(self.run_button)
        self.result_card.body_layout.addWidget(self.result_table)
        layout.addWidget(self.result_card)

    def set_context(
        self,
        definitions: dict[str, dict[str, str]],
        results: list[dict[str, object]],
    ) -> None:
        entries = list(definitions.items())
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
