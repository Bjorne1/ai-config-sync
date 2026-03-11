from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QWidget

from ..widgets import ActionButton, BadgeLabel, CardFrame, HeaderBlock, MetricCard


class OverviewPage(QWidget):
    refresh_requested = Signal()
    sync_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.header = HeaderBlock(
            "01 / Overview",
            "编辑部总控台",
            "工业灰 + 安全橙的作业面板，把资源、环境和最近动作放在同一张工单上。",
        )
        layout.addWidget(self.header, 0, 0, 1, 2)
        self.summary_card = CardFrame("运行视图", "当前同步模式、源目录和最近动作。")
        self.metric_grid = QGridLayout()
        self.metric_grid.setSpacing(14)
        self.metrics = [MetricCard(label) for label in ("已纳管 Skills", "已纳管 Commands", "目标通道", "异常条目")]
        for index, card in enumerate(self.metrics):
            self.metric_grid.addWidget(card, index // 2, index % 2)
        self.summary_card.body_layout.addLayout(self._build_badges())
        self.summary_card.body_layout.addLayout(self._build_actions())
        self.summary_card.body_layout.addWidget(self._label_block("Source Deck"))
        self.summary_card.body_layout.addWidget(self._label_block("最近同步"))
        layout.addWidget(self.summary_card, 1, 0)
        layout.addLayout(self.metric_grid, 1, 1)

    def _build_badges(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        self.mode_badge = BadgeLabel("SYMLINK", "healthy")
        self.wsl_badge = BadgeLabel("WSL OFF", "idle")
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

    def _label_block(self, title: str) -> QWidget:
        block = CardFrame(title)
        block.setObjectName("metricCard")
        label = QLabel("--")
        label.setObjectName("muted")
        label.setWordWrap(True)
        if title == "Source Deck":
            self.source_label = label
        else:
            self.sync_label = label
        block.body_layout.addWidget(label)
        return block

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
        self.wsl_badge.setText("WSL ON" if snapshot["config"]["environments"]["wsl"]["enabled"] else "WSL OFF")
        self.wsl_badge.set_state("partial" if snapshot["config"]["environments"]["wsl"]["enabled"] else "idle")
        self.issue_badge.setText("需处理" if issue_count else "运行平稳")
        self.issue_badge.set_state("conflict" if issue_count else "healthy")
        self.source_label.setText(
            f"{snapshot['config']['sourceDirs']['skills']}\n{snapshot['config']['sourceDirs']['commands']}"
        )
        log_text = "尚未执行动作" if not latest_log else f"{latest_log['label']} · {latest_log['detail']}"
        sync_text = last_sync_summary or "尚未执行同步批次"
        self.sync_label.setText(f"{sync_text}\n{log_text}")
        for card, stat in zip(self.metrics, stats, strict=True):
            card.set_value(stat["value"], stat["note"])

    def set_busy(self, refresh_busy: bool, sync_busy: bool) -> None:
        self.refresh_button.set_busy(refresh_busy)
        self.sync_button.set_busy(sync_busy)
