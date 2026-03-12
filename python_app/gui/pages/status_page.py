from PySide6.QtWidgets import QGridLayout, QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ..dashboard import STATE_LABELS
from ..widgets import CardFrame, configure_table, layout_container


class StatusPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_top_row())
        layout.addWidget(self._build_issue_card(), 1)

    def _build_top_row(self) -> QWidget:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 7)
        grid.addWidget(self._build_environment_card(), 0, 0)
        grid.addWidget(self._build_log_card(), 0, 1)
        return layout_container(grid)

    def _build_environment_card(self) -> QWidget:
        self.environment_card = CardFrame("环境状态", "当前 Windows / WSL 运行时与关键目录映射。")
        self.environment_table = QTableWidget(0, 4)
        self.environment_table.setHorizontalHeaderLabels(("环境", "状态", "Skills 根", "Commands 根"))
        configure_table(self.environment_table, stretch_columns=(2, 3))
        self.environment_table.setMaximumHeight(190)
        self.environment_card.body_layout.addWidget(self.environment_table)
        return self.environment_card

    def _build_log_card(self) -> QWidget:
        self.log_card = CardFrame("动作日志", "最近同步摘要与最近 6 条控制器动作。")
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(190)
        self.log_card.body_layout.addWidget(self.log_view)
        return self.log_card

    def _build_issue_card(self) -> QWidget:
        self.issue_card = CardFrame("异常列表", "按资源、环境和目标路径汇总当前待处理项。")
        self.issue_table = QTableWidget(0, 5)
        self.issue_table.setHorizontalHeaderLabels(("资源", "环境", "工具", "状态", "目标"))
        configure_table(self.issue_table, stretch_columns=(0, 4))
        self.issue_card.body_layout.addWidget(self.issue_table)
        return self.issue_card

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
        self.log_view.setPlainText(f"最近同步摘要：{sync_text}\n\n{log_text}")

    def _fill_environment_table(self, environments: dict[str, object]) -> None:
        rows = list(environments.values())
        self.environment_table.setRowCount(len(rows))
        for row_index, environment in enumerate(rows):
            values = [
                environment["label"],
                "可用" if environment["enabled"] else "不可用",
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
                STATE_LABELS.get(issue["state"], issue["state"]),
                issue.get("targetPath") or issue["message"],
            ]
            for column, value in enumerate(values):
                self.issue_table.setItem(row_index, column, QTableWidgetItem(str(value)))
