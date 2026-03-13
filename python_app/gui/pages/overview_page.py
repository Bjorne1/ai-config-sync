from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..dashboard import STATE_LABELS, has_wsl_assignments
from ..widgets import ActionButton, BadgeLabel, CardFrame, MetricCard, configure_table, layout_container


class OverviewPage(QWidget):
    refresh_requested = Signal()
    sync_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 8)
        layout.setSpacing(12)
        layout.addWidget(self._build_metric_strip())
        layout.addWidget(self._build_board())
        layout.addWidget(self._build_env_log_row())
        layout.addWidget(self._build_issue_card(), 1)

    def _build_metric_strip(self) -> QWidget:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        self.metrics = [MetricCard(label) for label in ("已配置 Skills", "已配置 Commands", "同步目标", "待处理")]
        for index, card in enumerate(self.metrics):
            grid.addWidget(card, 0, index)
            grid.setColumnStretch(index, 1)
        return layout_container(grid)

    def _build_board(self) -> QWidget:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(0, 7)
        grid.setColumnStretch(1, 5)
        grid.addWidget(self._build_summary_card(), 0, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(self._build_context_column(), 0, 1)
        return layout_container(grid)

    def _build_summary_card(self) -> QWidget:
        self.summary_card = CardFrame("运行状态", "当前同步模式与 WSL 状态。")
        self.summary_card.body_layout.addLayout(self._build_badges())
        self.summary_note = QLabel("正在加载…")
        self.summary_note.setObjectName("muted")
        self.summary_note.setWordWrap(True)
        self.summary_card.body_layout.addWidget(self.summary_note)
        self.summary_card.body_layout.addLayout(self._build_actions())
        return self.summary_card

    def _build_context_column(self) -> QWidget:
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(16)
        column.addWidget(self._build_context_card("来源目录", "Skills 与 Commands 的源目录。", "source"))
        column.addWidget(self._build_context_card("最近同步", "上次同步结果与最后一条操作记录。", "sync"))
        return layout_container(column)

    def _build_context_card(self, title: str, detail: str, key: str) -> QWidget:
        card = CardFrame(title, detail)
        label = QLabel("--")
        label.setObjectName("muted")
        label.setWordWrap(True)
        card.body_layout.addWidget(label)
        if key == "source":
            self.source_label = label
        else:
            self.sync_label = label
        return card

    def _build_badges(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        self.mode_badge = BadgeLabel("SYMLINK", "healthy")
        self.wsl_badge = BadgeLabel("WSL IDLE", "idle")
        self.issue_badge = BadgeLabel("正常", "healthy")
        row.addWidget(self.mode_badge)
        row.addWidget(self.wsl_badge)
        row.addWidget(self.issue_badge)
        row.addStretch(1)
        return row

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        self.refresh_button = ActionButton("刷新总览", "secondary")
        self.sync_button = ActionButton("同步全部资源", "primary")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.sync_button.clicked.connect(self.sync_all_requested.emit)
        row.addWidget(self.refresh_button)
        row.addWidget(self.sync_button)
        row.addStretch(1)
        return row

    def _build_env_log_row(self) -> QWidget:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)
        grid.setColumnStretch(0, 6)
        grid.setColumnStretch(1, 5)
        grid.addWidget(self._build_environment_card(), 0, 0)
        grid.addWidget(self._build_log_card(), 0, 1)
        return layout_container(grid)

    def _build_environment_card(self) -> QWidget:
        card = CardFrame("环境信息", "Windows / WSL 运行时与目录路径。")
        self.environment_table = QTableWidget(0, 4)
        self.environment_table.setHorizontalHeaderLabels(("环境", "状态", "Skills 根", "Commands 根"))
        configure_table(self.environment_table, stretch_columns=(2, 3))
        self.environment_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.environment_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        card.body_layout.addWidget(self.environment_table)
        return card

    def _build_log_card(self) -> QWidget:
        card = CardFrame("操作日志", "最近同步结果与最近 6 条操作记录。")
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        card.body_layout.addWidget(self.log_view)
        return card

    def _build_issue_card(self) -> QWidget:
        card = CardFrame("异常列表", "按资源、环境和目标路径汇总的待处理项。")
        self.issue_table = QTableWidget(0, 5)
        self.issue_table.setHorizontalHeaderLabels(("资源", "环境", "工具", "状态", "目标"))
        configure_table(self.issue_table, stretch_columns=(0, 4))
        self.issue_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.issue_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        card.body_layout.addWidget(self.issue_table)
        return card

    def set_context(
        self,
        stats: list[dict[str, str]],
        snapshot: dict[str, object],
        latest_log: dict[str, str] | None,
        last_sync_summary: str | None,
        issue_count: int,
        environments: dict[str, object],
        issues: list[dict[str, object]],
        logs: list[dict[str, str]],
    ) -> None:
        self.mode_badge.setText(snapshot["config"]["syncMode"].upper())
        self.mode_badge.set_state("partial" if snapshot["config"]["syncMode"] == "copy" else "healthy")
        wsl_active = has_wsl_assignments(snapshot["config"]["resources"])
        self.wsl_badge.setText("WSL ACTIVE" if wsl_active else "WSL IDLE")
        self.wsl_badge.set_state("partial" if wsl_active else "idle")
        self.issue_badge.setText("需处理" if issue_count else "正常")
        self.issue_badge.set_state("ahead" if issue_count else "healthy")
        source_text = f"{snapshot['config']['sourceDirs']['skills']}\n{snapshot['config']['sourceDirs']['commands']}"
        self.source_label.setText(source_text)
        sync_text = last_sync_summary or "尚未同步"
        log_text = "暂无操作记录" if not latest_log else f"{latest_log['label']} · {latest_log['detail']}"
        self.sync_label.setText(f"{sync_text}\n{log_text}")
        self.summary_note.setText(
            f"当前为 {snapshot['config']['syncMode']} 模式，"
            f"{'WSL 已加入同步' if wsl_active else 'WSL 未加入同步'}，"
            f"共 {issue_count} 条待处理。"
        )
        for card, stat in zip(self.metrics, stats, strict=True):
            card.set_value(stat["value"], stat["note"])
        self._fill_environment_table(environments)
        self._fill_issue_table(issues)
        log_lines = "\n".join(
            f"[{entry['time']}] {entry['label']} · {entry['detail']}" for entry in logs
        ) or "暂无记录"
        self.log_view.setPlainText(f"最近同步：{sync_text}\n\n{log_lines}")

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
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.environment_table.setItem(row_index, column, item)

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

    def set_busy(self, refresh_busy: bool, sync_busy: bool) -> None:
        self.refresh_button.set_busy(refresh_busy)
        self.sync_button.set_busy(sync_busy)
