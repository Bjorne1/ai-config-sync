from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
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
from .event_filters import WheelBlocker
from .pages.cleanup_page import CleanupPage
from .pages.config_page import ConfigPage
from .pages.global_rule_page import GlobalRulePage
from .pages.overview_page import OverviewPage
from .pages.resource_page import ResourcePage
from .pages.skill_upstream_page import SkillUpstreamPage
from .pages.tools_page import ToolsPage
from .theme import build_stylesheet
from .widgets import NavButton

PAGE_KEYS = (
    "overview",
    "skills",
    "skillUpstreams",
    "commands",
    "globalRules",
    "config",
    "cleanup",
    "tools",
)
PAGE_LABELS = ("概览", "Skills", "Skills 上游", "Commands", "全局规则", "配置", "清理", "工具更新")


class MainWindow(QMainWindow):
    refresh_requested = Signal()
    sync_all_requested = Signal()
    rescan_requested = Signal(str)
    sync_selected_requested = Signal(str, object)
    global_rule_refresh_requested = Signal()
    global_rule_profiles_save_requested = Signal(object)
    global_rule_assignments_save_requested = Signal(object)
    global_rule_sync_requested = Signal(object)
    reload_wsl_requested = Signal()
    save_config_requested = Signal(object)
    cleanup_requested = Signal()
    update_tools_requested = Signal()
    update_tool_requested = Signal(str)
    save_tool_definitions_requested = Signal(object)
    skill_add_requested = Signal(object)
    skill_set_url_requested = Signal(object)
    skill_check_requested = Signal(object)
    skill_upgrade_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: dict[str, object] | None = None
        self.logs: list[dict[str, str]] = []
        self.last_sync_summary: str | None = None
        self.cleanup_result: dict[str, object] | None = None
        self.tool_results: list[dict[str, object]] = []
        self.update_tool_statuses: dict[str, dict[str, object]] = {}
        self.busy: dict[str, bool] = {}
        self.setWindowTitle("AI Config Sync")
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.resize(min(1520, int(avail.width() * 0.85)),
                        min(960, int(avail.height() * 0.85)))
        else:
            self.resize(1520, 960)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        self.setStyleSheet(build_stylesheet())
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_workspace(), 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(0)
        hero = QFrame()
        hero.setObjectName("sidebarHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 18, 16, 18)
        hero_layout.setSpacing(6)
        title = QLabel("Boss Console\nRenderer")
        title.setObjectName("sidebarTitle")
        title.setWordWrap(True)
        intro = QLabel("工业灰 + 安全橙\n紧凑布局，清晰易读。")
        intro.setObjectName("sidebarIntro")
        intro.setWordWrap(True)
        hero_layout.addWidget(title)
        hero_layout.addWidget(intro)
        layout.addWidget(hero)
        layout.addSpacing(16)
        section_label = QLabel("Navigation")
        section_label.setObjectName("sidebarSectionLabel")
        layout.addWidget(section_label)
        layout.addSpacing(8)
        # 导航按钮分组: 主功能 / 资源管理 / 系统
        NAV_GROUP_BREAKS = {"config", "cleanup"}
        self.nav_buttons: dict[str, NavButton] = {}
        for key, label in zip(PAGE_KEYS, PAGE_LABELS, strict=True):
            if key in NAV_GROUP_BREAKS:
                layout.addSpacing(12)
            button = NavButton(label)
            button.clicked.connect(lambda _=False, page_key=key: self.set_current_page(page_key))
            layout.addWidget(button)
            layout.addSpacing(4)
            self.nav_buttons[key] = button
        layout.addStretch(1)
        return sidebar

    def _build_workspace(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("workspace")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.error_banner = QLabel("")
        self.error_banner.setWordWrap(True)
        self.error_banner.hide()
        self.error_banner.setStyleSheet("border: 1px solid #b91c1c; border-radius: 14px; padding: 10px 12px; background: #fee2e2; color: #991b1b;")
        layout.addWidget(self.error_banner)
        self.workspace_scroll = QScrollArea()
        self.workspace_scroll.setObjectName("workspaceScroll")
        self.workspace_scroll.setWidgetResizable(True)
        layout.addWidget(self.workspace_scroll, 1)
        self._workspace_wheel_blocker = WheelBlocker(self.workspace_scroll)
        self.workspace_scroll.installEventFilter(self._workspace_wheel_blocker)
        self.workspace_scroll.viewport().installEventFilter(self._workspace_wheel_blocker)
        container = QWidget()
        self.workspace_scroll.setWidget(container)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        self.pages = QStackedWidget()
        self.pages.setObjectName("pageStack")
        container_layout.addWidget(self.pages)
        self._create_pages()
        return wrapper

    def _create_pages(self) -> None:
        self.overview_page = OverviewPage()
        self.skills_page = ResourcePage("skills")
        self.skill_upstream_page = SkillUpstreamPage()
        self.commands_page = ResourcePage("commands")
        self.global_rule_page = GlobalRulePage()
        self.config_page = ConfigPage()
        self.cleanup_page = CleanupPage()
        self.tools_page = ToolsPage()
        page_list = [
            self.overview_page,
            self.skills_page,
            self.skill_upstream_page,
            self.commands_page,
            self.global_rule_page,
            self.config_page,
            self.cleanup_page,
            self.tools_page,
        ]
        for page in page_list:
            self.pages.addWidget(page)
        self.overview_page.refresh_requested.connect(self.refresh_requested.emit)
        self.overview_page.sync_all_requested.connect(self.sync_all_requested.emit)
        self.skills_page.rescan_requested.connect(self.rescan_requested.emit)
        self.skills_page.sync_requested.connect(self.sync_selected_requested.emit)
        self.skill_upstream_page.add_requested.connect(self.skill_add_requested.emit)
        self.skill_upstream_page.set_url_requested.connect(self.skill_set_url_requested.emit)
        self.skill_upstream_page.check_requested.connect(self.skill_check_requested.emit)
        self.skill_upstream_page.upgrade_requested.connect(self.skill_upgrade_requested.emit)
        self.commands_page.rescan_requested.connect(self.rescan_requested.emit)
        self.commands_page.sync_requested.connect(self.sync_selected_requested.emit)
        self.global_rule_page.refresh_requested.connect(self.global_rule_refresh_requested.emit)
        self.global_rule_page.save_profiles_requested.connect(
            self.global_rule_profiles_save_requested.emit
        )
        self.global_rule_page.save_assignments_requested.connect(
            self.global_rule_assignments_save_requested.emit
        )
        self.global_rule_page.sync_requested.connect(self.global_rule_sync_requested.emit)
        self.config_page.reload_requested.connect(self.reload_wsl_requested.emit)
        self.config_page.save_requested.connect(self.save_config_requested.emit)
        self.cleanup_page.cleanup_requested.connect(self.cleanup_requested.emit)
        self.tools_page.update_requested.connect(self.update_tools_requested.emit)
        self.tools_page.update_tool_requested.connect(self.update_tool_requested.emit)
        self.tools_page.definitions_save_requested.connect(self.save_tool_definitions_requested.emit)
        self.set_current_page("overview")

    def set_current_page(self, key: str) -> None:
        index = PAGE_KEYS.index(key)
        self.pages.setCurrentIndex(index)
        for page_key, button in self.nav_buttons.items():
            button.set_active(page_key == key)
        self._update_workspace_scroll_policy(key)

    def _update_workspace_scroll_policy(self, key: str) -> None:
        self.workspace_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.workspace_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.workspace_scroll.verticalScrollBar().setEnabled(True)
        self.workspace_scroll.horizontalScrollBar().setEnabled(True)
        self._workspace_wheel_blocker.set_enabled(False)

    def set_snapshot(self, snapshot: dict[str, object]) -> None:
        self.snapshot = deepcopy(snapshot)
        statuses = snapshot.get("updateToolStatuses", {})
        if isinstance(statuses, dict):
            self.update_tool_statuses = deepcopy(statuses)
        else:
            self.update_tool_statuses = {}
        self._refresh_views()

    def set_update_tool_statuses(self, statuses: dict[str, dict[str, object]]) -> None:
        self.update_tool_statuses = deepcopy(statuses) if isinstance(statuses, dict) else {}
        if not self.snapshot:
            return
        self.tools_page.set_context(
            self.snapshot["config"]["updateTools"],
            self.tool_results,
            self.update_tool_statuses,
        )
        self._refresh_busy()

    def set_skill_update_results(self, results: list[dict[str, object]]) -> None:
        self.skill_upstream_page.set_update_results(results)
        self._refresh_busy()

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

    def get_assignments(self, kind: str) -> dict[str, dict[str, list[str]]]:
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
        self.overview_page.set_context(
            stats, self.snapshot, latest_log, self.last_sync_summary, len(issues),
            self.snapshot["status"]["environments"], issues, self.logs,
        )
        self.skills_page.set_rows(self._resource_rows("skills"))
        self.skill_upstream_page.set_context(
            self.snapshot["inventory"]["skills"],
            self.snapshot.get("skillUpstreams", {}),
        )
        self.commands_page.set_rows(self._resource_rows("commands"))
        self.global_rule_page.set_context(
            self.snapshot.get("globalRules", {}),
            self.snapshot.get("globalRuleStatus", []),
        )
        self.config_page.set_context(self.snapshot["config"], self.snapshot["wslRuntime"])
        self.cleanup_page.set_context(cleanup_candidates, self.cleanup_result)
        self.tools_page.set_context(
            self.snapshot["config"]["updateTools"],
            self.tool_results,
            self.update_tool_statuses,
        )
        self._refresh_busy()

    def _resource_rows(self, kind: str) -> list[dict[str, object]]:
        return build_resource_rows(
            kind,
            self.snapshot["inventory"][kind],
            self.snapshot["config"]["resources"][kind],
            self.snapshot["status"][kind],
            self.snapshot["config"],
            self.snapshot["status"]["environments"],
        )

    def _refresh_busy(self) -> None:
        self.overview_page.set_busy(self._busy("refresh"), self._busy("syncAll"))
        self.skills_page.set_busy(self._busy("scanSkills"), self._busy("syncSkills"))
        self.skill_upstream_page.set_busy(
            self._busy("skillAdd") or self._busy("skillSetUrl") or self._busy("skillCheck") or self._busy("skillUpgrade")
        )
        self.commands_page.set_busy(self._busy("scanCommands"), self._busy("syncCommands"))
        self.global_rule_page.set_busy(
            self._busy("refreshGlobalRules"),
            self._busy("saveGlobalRuleProfiles"),
            self._busy("saveGlobalRuleAssignments"),
            self._busy("syncGlobalRules"),
        )
        self.config_page.set_busy(self._busy("reloadWsl"), self._busy("saveConfig"))
        self.cleanup_page.set_busy(self._busy("cleanup"))
        self.tools_page.set_busy(
            self._busy("updateTools") or self._busy("updateTool"),
            self._busy("saveToolDefinitions"),
        )

    def _busy(self, key: str) -> bool:
        if key in self.busy:
            return self.busy[key]
        snake = "".join([f"_{char.lower()}" if char.isupper() else char for char in key]).lstrip("_")
        return self.busy.get(snake, False)
