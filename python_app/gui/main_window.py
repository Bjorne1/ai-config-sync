from copy import deepcopy

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .dashboard import build_issue_rows, build_resource_rows, count_cleanup_candidates, overview_stats
from .pages.cleanup_page import CleanupPage
from .pages.config_page import ConfigPage
from .pages.overview_page import OverviewPage
from .pages.resource_page import ResourcePage
from .pages.status_page import StatusPage
from .pages.tools_page import ToolsPage
from .theme import build_stylesheet
from .widgets import NavButton

PAGE_KEYS = ("overview", "skills", "commands", "status", "config", "cleanup", "tools")
PAGE_LABELS = ("概览", "Skills", "Commands", "状态", "配置", "清理", "工具更新")


class MainWindow(QMainWindow):
    refresh_requested = Signal()
    sync_all_requested = Signal()
    rescan_requested = Signal(str)
    save_assignments_requested = Signal(str, object)
    sync_selected_requested = Signal(str, object)
    reload_wsl_requested = Signal()
    save_config_requested = Signal(object)
    cleanup_requested = Signal()
    update_tools_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: dict[str, object] | None = None
        self.logs: list[dict[str, str]] = []
        self.last_sync_summary: str | None = None
        self.cleanup_result: dict[str, object] | None = None
        self.tool_results: list[dict[str, object]] = []
        self.busy: dict[str, bool] = {}
        self.setWindowTitle("AI Config Sync")
        self.resize(1520, 960)
        self.setStyleSheet(build_stylesheet())
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_workspace(), 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(248)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(12)
        title = QLabel("Boss Console\nRenderer")
        title.setStyleSheet("color: white; font-size: 26px; font-weight: 700;")
        intro = QLabel("Industrial grey + safety orange.\n高密度视图，不牺牲可读性。")
        intro.setStyleSheet("color: #cbd5e1;")
        intro.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(intro)
        self.nav_buttons: dict[str, NavButton] = {}
        for key, label in zip(PAGE_KEYS, PAGE_LABELS, strict=True):
            button = NavButton(label)
            button.clicked.connect(lambda _=False, page_key=key: self.set_current_page(page_key))
            layout.addWidget(button)
            self.nav_buttons[key] = button
        layout.addStretch(1)
        return sidebar

    def _build_workspace(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.error_banner = QLabel("")
        self.error_banner.setWordWrap(True)
        self.error_banner.hide()
        self.error_banner.setStyleSheet("border: 1px solid #b91c1c; border-radius: 14px; padding: 10px 12px; background: #fee2e2; color: #991b1b;")
        layout.addWidget(self.error_banner)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)
        container = QWidget()
        scroll.setWidget(container)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        self.pages = QStackedWidget()
        container_layout.addWidget(self.pages)
        self._create_pages()
        return wrapper

    def _create_pages(self) -> None:
        self.overview_page = OverviewPage()
        self.skills_page = ResourcePage("skills")
        self.commands_page = ResourcePage("commands")
        self.status_page = StatusPage()
        self.config_page = ConfigPage()
        self.cleanup_page = CleanupPage()
        self.tools_page = ToolsPage()
        page_list = [
            self.overview_page,
            self.skills_page,
            self.commands_page,
            self.status_page,
            self.config_page,
            self.cleanup_page,
            self.tools_page,
        ]
        for page in page_list:
            self.pages.addWidget(page)
        self.overview_page.refresh_requested.connect(self.refresh_requested.emit)
        self.overview_page.sync_all_requested.connect(self.sync_all_requested.emit)
        self.skills_page.rescan_requested.connect(self.rescan_requested.emit)
        self.skills_page.save_requested.connect(self.save_assignments_requested.emit)
        self.skills_page.sync_requested.connect(self.sync_selected_requested.emit)
        self.commands_page.rescan_requested.connect(self.rescan_requested.emit)
        self.commands_page.save_requested.connect(self.save_assignments_requested.emit)
        self.commands_page.sync_requested.connect(self.sync_selected_requested.emit)
        self.config_page.reload_requested.connect(self.reload_wsl_requested.emit)
        self.config_page.save_requested.connect(self.save_config_requested.emit)
        self.cleanup_page.cleanup_requested.connect(self.cleanup_requested.emit)
        self.tools_page.update_requested.connect(self.update_tools_requested.emit)
        self.set_current_page("overview")

    def set_current_page(self, key: str) -> None:
        index = PAGE_KEYS.index(key)
        self.pages.setCurrentIndex(index)
        for page_key, button in self.nav_buttons.items():
            button.set_active(page_key == key)

    def set_snapshot(self, snapshot: dict[str, object]) -> None:
        self.snapshot = deepcopy(snapshot)
        self._refresh_views()

    def set_logs(self, logs: list[dict[str, str]]) -> None:
        self.logs = deepcopy(logs)
        self._refresh_views()

    def set_last_sync_summary(self, summary: str | None) -> None:
        self.last_sync_summary = summary
        self._refresh_views()

    def set_cleanup_result(self, result: dict[str, object] | None) -> None:
        self.cleanup_result = deepcopy(result)
        self._refresh_views()

    def set_tool_results(self, results: list[dict[str, object]]) -> None:
        self.tool_results = deepcopy(results)
        self._refresh_views()

    def set_error_message(self, message: str | None) -> None:
        self.error_banner.setVisible(bool(message))
        self.error_banner.setText(message or "")

    def set_busy(self, busy: dict[str, bool]) -> None:
        self.busy = {**busy}
        self._refresh_busy()

    def get_assignments(self, kind: str) -> dict[str, list[str]]:
        page = self.skills_page if kind == "skills" else self.commands_page
        return page.get_assignments()

    def get_config_patch(self) -> dict[str, object]:
        return self.config_page.get_patch()

    def _refresh_views(self) -> None:
        if not self.snapshot:
            return
        issues = build_issue_rows(self.snapshot)
        cleanup_candidates = count_cleanup_candidates(issues)
        stats = overview_stats(self.snapshot, len(issues), cleanup_candidates)
        latest_log = self.logs[0] if self.logs else None
        self.overview_page.set_context(stats, self.snapshot, latest_log, self.last_sync_summary, len(issues))
        self.skills_page.set_rows(self._resource_rows("skills"))
        self.commands_page.set_rows(self._resource_rows("commands"))
        self.status_page.set_context(self.snapshot["status"]["environments"], issues, self.logs, self.last_sync_summary)
        self.config_page.set_context(self.snapshot["config"], self.snapshot["wslRuntime"])
        self.cleanup_page.set_context(cleanup_candidates, self.cleanup_result)
        self.tools_page.set_context(self.snapshot["config"]["updateTools"], self.tool_results)
        self._refresh_busy()

    def _resource_rows(self, kind: str) -> list[dict[str, object]]:
        return build_resource_rows(
            kind,
            self.snapshot["inventory"][kind],
            self.snapshot["config"]["resources"][kind],
            self.snapshot["status"][kind],
        )

    def _refresh_busy(self) -> None:
        self.overview_page.set_busy(self._busy("refresh"), self._busy("syncAll"))
        self.skills_page.set_busy(self._busy("scanSkills"), self._busy("saveSkills"), self._busy("syncSkills"))
        self.commands_page.set_busy(self._busy("scanCommands"), self._busy("saveCommands"), self._busy("syncCommands"))
        self.config_page.set_busy(self._busy("reloadWsl"), self._busy("saveConfig"))
        self.cleanup_page.set_busy(self._busy("cleanup"))
        self.tools_page.set_busy(self._busy("updateTools"))

    def _busy(self, key: str) -> bool:
        if key in self.busy:
            return self.busy[key]
        snake = "".join([f"_{char.lower()}" if char.isupper() else char for char in key]).lstrip("_")
        return self.busy.get(snake, False)
