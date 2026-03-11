from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ..widgets import CardFrame, HeaderBlock


class StatusPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(HeaderBlock("04 / Status", "状态台账", "环境状态、异常条目和动作日志放在同一页，便于直接定位问题。"))
        self.environment_card = CardFrame("环境状态")
        self.environment_table = QTableWidget(0, 4)
        self.environment_table.setHorizontalHeaderLabels(("环境", "启用", "Skills 根", "Commands 根"))
        self.environment_table.verticalHeader().setVisible(False)
        self.environment_card.body_layout.addWidget(self.environment_table)
        layout.addWidget(self.environment_card)
        self.issue_card = CardFrame("异常列表")
        self.issue_table = QTableWidget(0, 5)
        self.issue_table.setHorizontalHeaderLabels(("资源", "环境", "工具", "状态", "目标"))
        self.issue_table.verticalHeader().setVisible(False)
        self.issue_card.body_layout.addWidget(self.issue_table)
        layout.addWidget(self.issue_card)
        self.log_card = CardFrame("动作日志")
        self.log_label = QLabel("暂无日志。")
        self.log_label.setWordWrap(True)
        self.log_card.body_layout.addWidget(self.log_label)
        layout.addWidget(self.log_card)

    def set_context(
        self,
        environments: dict[str, object],
        issues: list[dict[str, object]],
        logs: list[dict[str, str]],
        last_sync_summary: str | None,
    ) -> None:
        self._fill_environment_table(environments)
        self._fill_issue_table(issues)
        sync_text = last_sync_summary or "尚未同步"
        log_text = "\n".join(f"[{log['time']}] {log['label']} · {log['detail']}" for log in logs) or "暂无日志。"
        self.log_label.setText(f"最近同步摘要：{sync_text}\n\n{log_text}")

    def _fill_environment_table(self, environments: dict[str, object]) -> None:
        rows = list(environments.values())
        self.environment_table.setRowCount(len(rows))
        for row_index, environment in enumerate(rows):
            values = [
                environment["label"],
                "启用" if environment["enabled"] else "关闭",
                environment["targets"]["skills"]["claude"] or environment.get("error") or "不可用",
                environment["targets"]["commands"]["codex"] or environment.get("error") or "不可用",
            ]
            for column, value in enumerate(values):
                self.environment_table.setItem(row_index, column, QTableWidgetItem(value))

    def _fill_issue_table(self, issues: list[dict[str, object]]) -> None:
        self.issue_table.setRowCount(len(issues))
        for row_index, issue in enumerate(issues):
            values = [
                f"{issue['kind']} / {issue['name']}",
                issue["environmentId"],
                issue["toolId"],
                issue["state"],
                issue.get("targetPath") or issue["message"],
            ]
            for column, value in enumerate(values):
                self.issue_table.setItem(row_index, column, QTableWidgetItem(str(value)))
