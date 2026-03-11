from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ..dashboard import summarize_cleanup
from ..widgets import ActionButton, CardFrame, HeaderBlock


class CleanupPage(QWidget):
    cleanup_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(HeaderBlock("06 / Cleanup", "清理工单", "清理冲突目标、缺失目标和源失效配置项。"))
        self.summary_card = CardFrame("清理摘要")
        self.run_button = ActionButton("执行清理", "danger")
        self.run_button.clicked.connect(self.cleanup_requested.emit)
        self.summary_label = QTableWidget(0, 4)
        self.summary_label.setHorizontalHeaderLabels(("资源", "工具", "环境", "目标"))
        self.summary_label.verticalHeader().setVisible(False)
        self.summary_card.body_layout.addWidget(self.run_button)
        self.summary_card.body_layout.addWidget(self.summary_label)
        layout.addWidget(self.summary_card)

    def set_context(self, candidate_count: int, result: dict[str, object] | None) -> None:
        cleaned = result["cleaned"] if result else []
        self.summary_card._detail.setText(f"候选项 {candidate_count} 条 · {summarize_cleanup(cleaned)}")
        self.summary_label.setRowCount(len(cleaned))
        for row_index, item in enumerate(cleaned):
            values = [
                f"{item['kind']} / {item['name']}",
                item["toolId"],
                item["environmentId"],
                item.get("targetPath") or "",
            ]
            for column, value in enumerate(values):
                self.summary_label.setItem(row_index, column, QTableWidgetItem(str(value)))

    def set_busy(self, busy: bool) -> None:
        self.run_button.set_busy(busy)
