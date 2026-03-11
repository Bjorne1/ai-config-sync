from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..dashboard import has_wsl_assignments
from ..widgets import ActionButton, BadgeLabel, CardFrame, HeaderBlock, MetricCard, layout_container


class OverviewPage(QWidget):
    refresh_requested = Signal()
    sync_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(
            HeaderBlock(
                "01 / Overview",
                "编辑部总控台",
                "工业灰 + 安全橙的作业面板，把资源、环境和最近动作压缩进一张更紧凑的工单。",
            )
        )
        layout.addWidget(self._build_metric_strip())
        layout.addWidget(self._build_board())
        layout.addStretch(1)

    def _build_metric_strip(self) -> QWidget:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        self.metrics = [MetricCard(label) for label in ("已纳管 Skills", "已纳管 Commands", "目标通道", "异常条目")]
        for index, card in enumerate(self.metrics):
            grid.addWidget(card, 0, index)
            grid.setColumnStretch(index, 1)
        return layout_container(grid)

    def _build_board(self) -> QWidget:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 7)
        grid.setColumnStretch(1, 5)
        grid.addWidget(self._build_summary_card(), 0, 0)
        grid.addWidget(self._build_context_column(), 0, 1)
        return layout_container(grid)

    def _build_summary_card(self) -> QWidget:
        self.summary_card = CardFrame("运行视图", "当前同步模式、WSL 同步矩阵状态和动作入口集中在这一张卡里。")
        self.summary_card.body_layout.addLayout(self._build_badges())
        self.summary_note = QLabel("等待状态回填。")
        self.summary_note.setObjectName("muted")
        self.summary_note.setWordWrap(True)
        self.summary_card.body_layout.addWidget(self.summary_note)
        self.summary_card.body_layout.addLayout(self._build_actions())
        return self.summary_card

    def _build_context_column(self) -> QWidget:
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(self._build_context_card("Source Deck", "当前技能源与命令源。", "source"))
        column.addWidget(self._build_context_card("最近同步", "最近批次摘要与最后一条动作。", "sync"))
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
        self.issue_badge = BadgeLabel("运行平稳", "healthy")
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

    def set_context(
        self,
        stats: list[dict[str, str]],
        snapshot: dict[str, object],
        latest_log: dict[str, str] | None,
        last_sync_summary: str | None,
        issue_count: int,
    ) -> None:
        self.mode_badge.setText(snapshot["config"]["syncMode"].upper())
        self.mode_badge.set_state("partial" if snapshot["config"]["syncMode"] == "copy" else "healthy")
        wsl_active = has_wsl_assignments(snapshot["config"]["resources"])
        self.wsl_badge.setText("WSL ACTIVE" if wsl_active else "WSL IDLE")
        self.wsl_badge.set_state("partial" if wsl_active else "idle")
        self.issue_badge.setText("需处理" if issue_count else "运行平稳")
        self.issue_badge.set_state("conflict" if issue_count else "healthy")
        source_text = f"{snapshot['config']['sourceDirs']['skills']}\n{snapshot['config']['sourceDirs']['commands']}"
        self.source_label.setText(source_text)
        sync_text = last_sync_summary or "尚未执行同步批次"
        log_text = "尚未执行动作" if not latest_log else f"{latest_log['label']} · {latest_log['detail']}"
        self.sync_label.setText(f"{sync_text}\n{log_text}")
        self.summary_note.setText(
            f"当前为 {snapshot['config']['syncMode']} 模式，"
            f"{'WSL 已纳入同步矩阵' if wsl_active else 'WSL 尚未纳入同步矩阵'}，"
            f"共检测到 {issue_count} 条待处理异常。"
        )
        for card, stat in zip(self.metrics, stats, strict=True):
            card.set_value(stat["value"], stat["note"])

    def set_busy(self, refresh_busy: bool, sync_busy: bool) -> None:
        self.refresh_button.set_busy(refresh_busy)
        self.sync_button.set_busy(sync_busy)
