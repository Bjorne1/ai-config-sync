from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ..dashboard import summarize_cleanup
from ..event_filters import WheelBlocker
from ..pagination import Pager, paginate
from ..widgets import ActionButton, CardFrame, configure_table

CLEANUP_ROWS_PER_PAGE = 10


class CleanupPage(QWidget):
    cleanup_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_index = 0
        self._page_size = CLEANUP_ROWS_PER_PAGE
        self._cleaned: list[dict[str, object]] = []
        self._visible: list[dict[str, object]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(self._build_summary_card())
        layout.addWidget(self._build_result_card(), 1)

    def _build_summary_card(self) -> QWidget:
        self.summary_card = CardFrame("清理概览", "待清理数量和上次清理结果。")
        self.summary_text = QLabel("正在扫描…")
        self.summary_text.setObjectName("muted")
        self.summary_text.setWordWrap(True)
        self.run_button = ActionButton("执行清理", "danger")
        self.run_button.clicked.connect(self.cleanup_requested.emit)
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 4, 0, 0)
        action_row.setSpacing(12)
        action_row.addWidget(self.summary_text, 1)
        action_row.addWidget(self.run_button, 0)
        self.summary_card.body_layout.addLayout(action_row)
        return self.summary_card

    def _build_result_card(self) -> QWidget:
        self.result_card = CardFrame("清理明细", "上次清理操作涉及的目标路径。")
        self.summary_table = QTableWidget(0, 4)
        self.summary_table.setHorizontalHeaderLabels(("资源", "工具", "环境", "目标"))
        configure_table(self.summary_table, stretch_columns=(0, 3))
        self.summary_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.summary_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table_wheel_blocker = WheelBlocker(self.summary_table)
        self._table_wheel_blocker.set_enabled(True)
        self.summary_table.viewport().installEventFilter(self._table_wheel_blocker)
        self.pager = Pager()
        self.pager.page_requested.connect(self._set_page)
        self.result_card.body_layout.addWidget(self.pager)
        self.result_card.body_layout.addWidget(self.summary_table, 1)
        return self.result_card

    def set_context(self, candidate_count: int, result: dict[str, object] | None) -> None:
        self._cleaned = list(result["cleaned"] if result else [])
        self.summary_text.setText(f"待清理 {candidate_count} 条 · {summarize_cleanup(self._cleaned)}")
        self._rebuild_table()

    def _set_page(self, index: int) -> None:
        self._page_index = index
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        self._visible, self._page_index, page_count, total = paginate(self._cleaned, self._page_index, self._page_size)
        self.summary_table.setRowCount(len(self._visible))
        for row_index, item in enumerate(self._visible):
            values = [
                f"{item['kind']} / {item['name']}",
                item["toolId"],
                item["environmentId"],
                item.get("targetPath") or "",
            ]
            for column, value in enumerate(values):
                self.summary_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.pager.set_state(self._page_index, page_count, total)

    def set_busy(self, busy: bool) -> None:
        self.run_button.set_busy(busy)
