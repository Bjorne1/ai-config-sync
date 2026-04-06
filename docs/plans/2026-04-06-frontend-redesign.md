# Frontend Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the PySide6 GUI from "industrial gray + safety orange" to a clean modern white theme (Notion/Linear style), merge the Skills Upstream page into the Skills resource page, and reduce page count from 8 to 7.

**Architecture:** Pure visual + structural refactor of the GUI layer. Core business logic (`python_app/core/**`) untouched. Data flow (Signal -> Controller -> Service -> UI) unchanged. Theme system rewritten with new color palette, sidebar redesigned, outer QScrollArea removed, SkillUpstreamPage absorbed into ResourcePage.

**Tech Stack:** Python 3.12+, PySide6 6.9+, Qt Style Sheets (QSS)

---

## Task 1: Rewrite Theme System

**Files:**
- Modify: `python_app/gui/theme.py` (full rewrite)
- Modify: `python_app/bootstrap.py:50` (font change)

**Step 1: Rewrite `theme.py` with new color palette, font system, and QSS**

Replace entire file content:

```python
from PySide6.QtGui import QColor, QFont

# --- Color Palette ---

# Backgrounds
WINDOW_BACKGROUND = "#f8fafc"
SURFACE = "#ffffff"
SURFACE_ALT = "#f1f5f9"
SURFACE_MUTED = "#e2e8f0"

# Sidebar
SIDEBAR = "#1e293b"
SIDEBAR_ALT = "#334155"

# Accent
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2563eb"
ACCENT_SOFT = "#eff6ff"

# Border
BORDER = "#e2e8f0"
BORDER_FOCUS = "#3b82f6"

# Status
SUCCESS = "#16a34a"
WARNING = "#d97706"
ERROR = "#dc2626"
INFO = "#3b82f6"

# Text
TEXT_PRIMARY = "#1e293b"
TEXT_SECONDARY = "#64748b"
TEXT_MUTED = "#94a3b8"

STATE_COLORS = {
    "healthy": (SUCCESS, "#dcfce7"),
    "missing": (WARNING, "#fef3c7"),
    "outdated": (WARNING, "#ffedd5"),
    "drifted": (ERROR, "#fee2e2"),
    "ahead": (ERROR, "#fee2e2"),
    "conflict": (ERROR, "#fee2e2"),
    "source_missing": (ERROR, "#fee2e2"),
    "tool_unavailable": (TEXT_MUTED, "#f1f5f9"),
    "environment_error": (ERROR, "#fee2e2"),
    "profile_missing": (ERROR, "#fee2e2"),
    "partial": (INFO, "#dbeafe"),
    "idle": (TEXT_MUTED, "#f1f5f9"),
    "detected": (WARNING, "#fef3c7"),
}


def create_app_font(size: int, weight: int = QFont.Weight.Normal) -> QFont:
    font = QFont("Segoe UI", size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setWeight(weight)
    return font


def create_mono_font(size: int, weight: int = QFont.Weight.Medium) -> QFont:
    font = QFont("Cascadia Code", size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setWeight(weight)
    return font


def tint(color: str, alpha: int) -> str:
    qcolor = QColor(color)
    qcolor.setAlpha(alpha)
    return qcolor.name(QColor.NameFormat.HexArgb)


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        color: {TEXT_PRIMARY};
        font-family: 'Segoe UI', 'Microsoft YaHei', system-ui, sans-serif;
        font-size: 13px;
    }}
    QLabel {{
        background: transparent;
    }}
    QMainWindow, QWidget#appRoot, QWidget#workspace {{
        background: {WINDOW_BACKGROUND};
    }}
    QStackedWidget#pageStack {{
        background: transparent;
        border: 0;
    }}
    QLabel#eyebrow {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.18em;
    }}
    QLabel#title {{
        color: {TEXT_PRIMARY};
        font-size: 18px;
        font-weight: 700;
    }}
    QLabel#sectionTitle {{
        color: {TEXT_PRIMARY};
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#muted {{
        color: {TEXT_SECONDARY};
    }}
    /* Sidebar */
    QFrame#sidebar {{
        background: {SIDEBAR};
        border: none;
        border-radius: 0;
    }}
    QLabel#sidebarTitle {{
        color: #f8fafc;
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#formLabel {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }}
    QPushButton#navButton {{
        background: transparent;
        border: none;
        border-left: 3px solid transparent;
        border-radius: 6px;
        color: {TEXT_MUTED};
        font-weight: 600;
        font-size: 13px;
        min-height: 38px;
        padding: 0 16px;
        text-align: left;
    }}
    QPushButton#navButton:hover {{
        background: rgba(51, 65, 85, 0.4);
        color: #e2e8f0;
    }}
    QPushButton#navButton[active="true"] {{
        background: {tint(ACCENT, 30)};
        border-left: 3px solid {ACCENT};
        color: #e2e8f0;
    }}
    /* Cards */
    QFrame#card {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    QFrame#metricCard {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    /* Buttons */
    QPushButton#primaryButton,
    QPushButton#secondaryButton,
    QPushButton#dangerButton {{
        border-radius: 6px;
        font-weight: 600;
        font-size: 13px;
        min-height: 32px;
        padding: 0 14px;
    }}
    QPushButton#primaryButton {{
        background: {ACCENT};
        border: 1px solid {ACCENT};
        color: white;
    }}
    QPushButton#primaryButton:hover {{
        background: {ACCENT_HOVER};
        border-color: {ACCENT_HOVER};
    }}
    QPushButton#primaryButton:pressed {{
        background: #1d4ed8;
        border-color: #1d4ed8;
    }}
    QPushButton#secondaryButton {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        color: {TEXT_PRIMARY};
    }}
    QPushButton#secondaryButton:hover {{
        background: {ACCENT_SOFT};
        border-color: {ACCENT};
        color: {ACCENT};
    }}
    QPushButton#secondaryButton:pressed {{
        background: #dbeafe;
        border-color: {ACCENT_HOVER};
        color: {ACCENT_HOVER};
    }}
    QPushButton#dangerButton {{
        background: {SURFACE};
        border: 1px solid {ERROR};
        color: {ERROR};
    }}
    QPushButton#dangerButton:hover {{
        background: #fef2f2;
        border-color: {ERROR};
    }}
    QPushButton#dangerButton:pressed {{
        background: #fee2e2;
        border-color: #b91c1c;
        color: #b91c1c;
    }}
    QPushButton:disabled {{
        opacity: 0.55;
    }}
    /* Inputs */
    QLineEdit, QComboBox, QPlainTextEdit, QTableWidget, QListWidget {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 6px;
        selection-background-color: {ACCENT};
        selection-color: white;
    }}
    QLineEdit, QComboBox, QPlainTextEdit {{
        padding: 6px 10px;
    }}
    QLineEdit, QComboBox {{
        min-height: 20px;
    }}
    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QListWidget:focus {{
        border: 1.5px solid {ACCENT};
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-bottom: 1px solid {SURFACE_ALT};
    }}
    QListWidget::item:selected {{
        background: {ACCENT_SOFT};
        color: {TEXT_PRIMARY};
    }}
    /* Tables */
    QTableWidget {{
        gridline-color: {SURFACE_ALT};
        alternate-background-color: {WINDOW_BACKGROUND};
        border-radius: 6px;
        padding: 0;
    }}
    QHeaderView::section {{
        background: {WINDOW_BACKGROUND};
        border: 0;
        border-bottom: 1px solid {BORDER};
        color: {TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 600;
        padding: 8px;
    }}
    QScrollArea {{
        border: 0;
        background: transparent;
    }}
    /* Checkbox */
    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {BORDER};
        background: {SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border-color: {ACCENT};
    }}
    QTabWidget::pane {{
        border: 0;
    }}
    /* Scrollbar */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(148, 163, 184, 0.35);
        border-radius: 3px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(148, 163, 184, 0.6);
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: rgba(148, 163, 184, 0.35);
        border-radius: 3px;
        min-width: 28px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: rgba(148, 163, 184, 0.6);
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0; width: 0;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}
    """
```

**Step 2: Update font in `bootstrap.py`**

In `python_app/bootstrap.py`, change line 50:
```python
    app.setFont(create_app_font(10))
```
No change needed — `create_app_font` now returns "Segoe UI" instead of "Fira Sans".

**Step 3: Verify compilation**

Run: `python -m compileall python_app`
Expected: all files compile without error.

**Step 4: Commit**

```bash
git add python_app/gui/theme.py
git commit -m "refactor(theme): rewrite color palette to modern blue-white style"
```

---

## Task 2: Update Widget Styles

**Files:**
- Modify: `python_app/gui/widgets.py:26-37` (shadow removal, card styles)
- Modify: `python_app/gui/widgets.py:62-107` (MetricCard hover colors)
- Modify: `python_app/gui/widgets.py:110-122` (BadgeLabel radius)

**Step 1: Remove card shadow utility and update CardFrame**

In `widgets.py`, remove the shadow parameters and `_apply_card_shadow` function (lines 26-37). Remove both calls to `_apply_card_shadow(self)` from `CardFrame.__init__` (line 44) and `MetricCard.__init__` (line 81). Remove the import of `QGraphicsDropShadowEffect` from the imports.

Replace lines 25-37:
```python
# (shadow removed — cards use border only per new design)
```

In `CardFrame.__init__`, remove the `_apply_card_shadow(self)` line (line 44).

In `MetricCard.__init__`, remove the `_apply_card_shadow(self)` line (line 81).

**Step 2: Update MetricCard hover styles to use new accent color**

Replace `MetricCard._STYLE_NORMAL` and `_STYLE_HOVER` (lines 63-74):
```python
    _STYLE_NORMAL = (
        f"QFrame#metricCard {{ background: {SURFACE};"
        f" border: 1px solid {BORDER};"
        f" border-radius: 8px; }}"
    )
    _STYLE_HOVER = (
        f"QFrame#metricCard {{ background: {SURFACE};"
        f" border: 1px solid {ACCENT};"
        f" border-radius: 8px; }}"
    )
```

Update the import line at the top of `widgets.py` to include the new constants:
```python
from .theme import ACCENT, BORDER, STATE_COLORS, SURFACE, create_mono_font
```
(This import already has what we need since `BORDER` and `ACCENT` are defined in the new theme.)

**Step 3: Update BadgeLabel border-radius**

In `BadgeLabel.set_state` (line 119-122), change `border-radius: 8px` to `border-radius: 4px` and adjust padding:
```python
    def set_state(self, state: str) -> None:
        fg, bg = STATE_COLORS.get(state, STATE_COLORS["idle"])
        self.setStyleSheet(
            f"border: 1px solid {fg}; border-radius: 4px;"
            f" padding: 2px 8px; color: {fg}; background: {bg};"
            f" font-size: 11px;"
        )
```

**Step 4: Verify compilation**

Run: `python -m compileall python_app`
Expected: all files compile without error.

**Step 5: Commit**

```bash
git add python_app/gui/widgets.py
git commit -m "refactor(widgets): update card, metric, badge styles for new theme"
```

---

## Task 3: Update Header Views and Pagination Colors

**Files:**
- Modify: `python_app/gui/header_views.py:7` (import update)
- Modify: `python_app/gui/pagination.py:8-15` (import update for new colors)

**Step 1: Update header_views.py imports**

The file imports `BORDER, SURFACE_ALT, TEXT_MUTED` from theme — these still exist in the new theme (with updated hex values), so no code changes needed. The visual change is automatic.

**Step 2: Update pagination.py colors**

In `pagination.py`, the imports reference `ACCENT, ACCENT_SOFT, BORDER, INFO, SUCCESS, TEXT_MUTED` — all still exist. The `TOOL_PILL_COLORS` dict on line 25-29 uses these:

```python
TOOL_PILL_COLORS: dict[str, tuple[str, str]] = {
    "claude": (ACCENT, ACCENT_SOFT),
    "codex": (SUCCESS, "#dcfce7"),
    "gemini": (INFO, "#dbeafe"),
    "antigravity": (ANTIGRAVITY_FG, ANTIGRAVITY_BG),
}
```

These will automatically pick up the new `ACCENT` (blue) and `ACCENT_SOFT` values. No changes needed.

**Step 3: Verify compilation**

Run: `python -m compileall python_app`
Expected: all files compile without error.

**Step 4: Commit**

```bash
git commit --allow-empty -m "style: header and pagination auto-adopt new theme colors"
```

---

## Task 4: Redesign Sidebar

**Files:**
- Modify: `python_app/gui/main_window.py:28-38` (PAGE_KEYS, PAGE_LABELS)
- Modify: `python_app/gui/main_window.py:92-130` (`_build_sidebar`)

**Step 1: Update page keys and labels (remove skillUpstreams)**

Replace lines 28-38:
```python
PAGE_KEYS = (
    "overview",
    "skills",
    "commands",
    "globalRules",
    "config",
    "cleanup",
    "tools",
)
PAGE_LABELS = ("概览", "Skills", "Commands", "全局规则", "配置", "清理", "工具更新")
```

**Step 2: Rewrite `_build_sidebar` for new design**

Replace `_build_sidebar` method (lines 92-130):
```python
    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(0)
        title = QLabel("AI Config Sync")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)
        layout.addSpacing(20)
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
```

This removes:
- The `sidebarHero` frame with "Boss Console Renderer" title and "工业灰 + 安全橙" intro
- The `sidebarSectionLabel` "Navigation" label
- Reduces width from 220px to 180px
- Replaces hero section with simple "AI Config Sync" title

**Step 3: Verify compilation**

Run: `python -m compileall python_app`
Expected: compile error because `_create_pages` still references `SkillUpstreamPage`. This is expected — we'll fix in Task 7.

**Step 4: Commit (partial — sidebar only)**

Do NOT commit yet. Continue to Task 5.

---

## Task 5: Remove Outer ScrollArea and SkillUpstreamPage

**Files:**
- Modify: `python_app/gui/main_window.py:1-15` (imports)
- Modify: `python_app/gui/main_window.py:132-158` (`_build_workspace`)
- Modify: `python_app/gui/main_window.py:160-205` (`_create_pages`)
- Modify: `python_app/gui/main_window.py:207-220` (`set_current_page`, remove scroll helper)
- Modify: `python_app/gui/main_window.py:241-243` (`set_skill_update_results`)
- Modify: `python_app/gui/main_window.py:276-340` (`_refresh_views`, `_refresh_busy`)

**Step 1: Update imports — remove QScrollArea, SkillUpstreamPage**

Replace lines 1-27:
```python
from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .dashboard import build_issue_rows, build_resource_rows, count_cleanup_candidates, overview_stats
from .pages.cleanup_page import CleanupPage
from .pages.config_page import ConfigPage
from .pages.global_rule_page import GlobalRulePage
from .pages.overview_page import OverviewPage
from .pages.resource_page import ResourcePage
from .pages.tools_page import ToolsPage
from .theme import build_stylesheet
from .widgets import NavButton
```

(Removed `QScrollArea` from QtWidgets, removed `from .event_filters import WheelBlocker`, removed `from .pages.skill_upstream_page import SkillUpstreamPage`)

**Step 2: Rewrite `_build_workspace` — remove QScrollArea wrapper**

Replace the `_build_workspace` method:
```python
    def _build_workspace(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("workspace")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.error_banner = QLabel("")
        self.error_banner.setWordWrap(True)
        self.error_banner.hide()
        self.error_banner.setStyleSheet(
            "border: 1px solid #dc2626; border-radius: 8px;"
            " padding: 10px 12px; background: #fee2e2; color: #991b1b;"
        )
        layout.addWidget(self.error_banner)
        self.pages = QStackedWidget()
        self.pages.setObjectName("pageStack")
        layout.addWidget(self.pages, 1)
        self._create_pages()
        return wrapper
```

**Step 3: Rewrite `_create_pages` — remove SkillUpstreamPage, add upstream signals from skills_page**

Replace `_create_pages`:
```python
    def _create_pages(self) -> None:
        self.overview_page = OverviewPage()
        self.skills_page = ResourcePage("skills")
        self.commands_page = ResourcePage("commands")
        self.global_rule_page = GlobalRulePage()
        self.config_page = ConfigPage()
        self.cleanup_page = CleanupPage()
        self.tools_page = ToolsPage()
        page_list = [
            self.overview_page,
            self.skills_page,
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
        self.skills_page.add_skill_requested.connect(self.skill_add_requested.emit)
        self.skills_page.set_url_requested.connect(self.skill_set_url_requested.emit)
        self.skills_page.check_upstream_requested.connect(self.skill_check_requested.emit)
        self.skills_page.upgrade_upstream_requested.connect(self.skill_upgrade_requested.emit)
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
```

Note: `add_skill_requested`, `set_url_requested`, `check_upstream_requested`, `upgrade_upstream_requested` are new signals on `ResourcePage` that we'll add in Task 6.

**Step 4: Simplify `set_current_page` — remove scroll policy helper**

Replace `set_current_page` and remove `_update_workspace_scroll_policy`:
```python
    def set_current_page(self, key: str) -> None:
        index = PAGE_KEYS.index(key)
        self.pages.setCurrentIndex(index)
        for page_key, button in self.nav_buttons.items():
            button.set_active(page_key == key)
```

**Step 5: Update `set_skill_update_results` to route to skills_page**

Replace `set_skill_update_results`:
```python
    def set_skill_update_results(self, results: list[dict[str, object]]) -> None:
        self.skills_page.set_update_results(results)
        self._refresh_busy()
```

**Step 6: Update `_refresh_views` — remove skill_upstream_page references**

Replace `_refresh_views`:
```python
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
        self.skills_page.set_upstream_context(
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
```

Note: `set_upstream_context` is a new method on ResourcePage we'll add in Task 6.

**Step 7: Update `_refresh_busy` — remove skill_upstream_page busy, add upstream busy to skills_page**

Replace `_refresh_busy`:
```python
    def _refresh_busy(self) -> None:
        upstream_busy = (
            self._busy("skillAdd")
            or self._busy("skillSetUrl")
            or self._busy("skillCheck")
            or self._busy("skillUpgrade")
        )
        self.overview_page.set_busy(self._busy("refresh"), self._busy("syncAll"))
        self.skills_page.set_busy(
            self._busy("scanSkills"),
            self._busy("syncSkills"),
            upstream_busy,
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
```

Note: `set_busy` on skills_page now takes 3 args (rescan, sync, upstream). We'll update that in Task 6.

**Step 8: Do NOT compile yet — ResourcePage changes are needed first. Continue to Task 6.**

---

## Task 6: Add Upstream Functionality to ResourcePage — Signals, Data, and Methods

**Files:**
- Modify: `python_app/gui/pages/resource_page.py` (add signals, data storage, upstream methods, action column logic, toolbar buttons)

This is the most complex task. We need to:
1. Add upstream-related signals to ResourcePage
2. Store upstream data (inventory, upstreams, update results)
3. Add `set_upstream_context` and `set_update_results` methods
4. Add upstream toolbar buttons (visible only for skills kind)
5. Change action column to show dynamic upstream status
6. Update `set_busy` signature to accept upstream_busy
7. Add dialog triggers and signal emission methods

**Step 1: Add new imports and signals**

At the top of `resource_page.py`, add to imports:
```python
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
```
(Add `QDialog` and `QMessageBox` to the import list.)

Add import for dialogs after the existing imports:
```python
from .skill_upstream_dialogs import AddSkillFromUrlDialog, SetSkillUrlDialog
```

Add new signals to the class definition (after `sync_requested`):
```python
class ResourcePage(QWidget):
    rescan_requested = Signal(str)
    sync_requested = Signal(str, object)
    add_skill_requested = Signal(object)
    set_url_requested = Signal(object)
    check_upstream_requested = Signal(object)
    upgrade_upstream_requested = Signal(object)
```

**Step 2: Add upstream instance variables to `__init__`**

After `self._display_items` in `__init__`:
```python
        self._upstream_inventory: list[dict[str, object]] = []
        self._upstreams: dict[str, dict[str, object]] = {}
        self._update_results: dict[str, dict[str, object]] = {}
```

**Step 3: Add upstream toolbar buttons to `_build_toolbar_card`**

In `_build_toolbar_card`, add buttons conditionally for skills kind. Replace the entire method:
```python
    def _build_toolbar_card(self) -> QWidget:
        card = CardFrame()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 1)
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"搜索 {self.kind} 名称或路径")
        self.search.textChanged.connect(self._handle_filter_changed)
        self.rescan_button = ActionButton("重新扫描", "secondary")
        self.sync_button = ActionButton("同步选中", "secondary")
        self.upgrade_button = ActionButton("全部升级", "secondary")
        self.remove_button = ActionButton("移除选中", "danger")
        self.rescan_button.clicked.connect(lambda: self.rescan_requested.emit(self.kind))
        self.sync_button.clicked.connect(self._emit_sync)
        self.upgrade_button.clicked.connect(self._emit_upgrade_all)
        self.remove_button.clicked.connect(self._emit_remove)
        col = 2
        grid.addWidget(self.search, 0, 0, 1, 2)
        grid.addWidget(self.rescan_button, 0, col); col += 1
        grid.addWidget(self.sync_button, 0, col); col += 1
        grid.addWidget(self.upgrade_button, 0, col); col += 1
        grid.addWidget(self.remove_button, 0, col); col += 1
        self.add_skill_button = None
        self.set_url_button = None
        self.check_button = None
        if self.kind == "skills":
            self.add_skill_button = ActionButton("新增 Skill", "secondary")
            self.set_url_button = ActionButton("设置 URL", "secondary")
            self.check_button = ActionButton("检查更新", "secondary")
            self.add_skill_button.clicked.connect(self._open_add_dialog)
            self.set_url_button.clicked.connect(self._open_set_url_dialog)
            self.check_button.clicked.connect(self._emit_check)
            grid.addWidget(self.add_skill_button, 0, col); col += 1
            grid.addWidget(self.set_url_button, 0, col); col += 1
            grid.addWidget(self.check_button, 0, col); col += 1
        self.meta = QLabel("0 条记录")
        self.meta.setObjectName("muted")
        grid.addWidget(self.meta, 1, 0, 1, col)
        card.body_layout.addLayout(grid)
        return card
```

**Step 4: Update action column rendering in `_fill_row`**

Replace the upgrade_item section at the end of `_fill_row` (around line 355-359):
```python
        action_text = self._action_column_text(row)
        action_item = QTableWidgetItem(action_text)
        action_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        action_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        action_item.setToolTip(self._action_column_tooltip(row))
        self.table.setItem(row_index, ACTION_COLUMN, action_item)
```

**Step 5: Add upstream action column logic methods**

Add these new methods to the class:
```python
    def _action_column_text(self, row: dict[str, object]) -> str:
        if self.kind != "skills":
            return "升级" if self._is_upgradeable_row(row) else ""
        name = row["name"]
        upstream = self._upstreams.get(name, {})
        url = str(upstream.get("url") or "").strip()
        if not url:
            return "设置 URL"
        update = self._update_results.get(name, {})
        if not update:
            return "检查"
        has_update = bool(update.get("latestCommit")) and update.get("latestCommit") != update.get("installedCommit")
        if has_update:
            return "升级"
        if self._is_upgradeable_row(row):
            return "升级"
        return "\u2713"

    def _action_column_tooltip(self, row: dict[str, object]) -> str:
        if self.kind != "skills":
            return "升级：同步缺失或有新版本的条目，跳过目标比源新的��目。"
        name = row["name"]
        upstream = self._upstreams.get(name, {})
        url = str(upstream.get("url") or "").strip()
        if not url:
            return "点击设置上游 URL"
        update = self._update_results.get(name, {})
        if not update:
            return "点击检查远程更新"
        has_update = bool(update.get("latestCommit")) and update.get("latestCommit") != update.get("installedCommit")
        if has_update:
            installed = str(update.get("installedCommit") or "未记录")[:8]
            latest = str(update.get("latestCommit") or "")[:8]
            return f"有新版本: {installed} → {latest}"
        if self._is_upgradeable_row(row):
            return "本地文件有更新可同步"
        return "已是最新"
```

**Step 6: Update `_handle_upgrade_clicked` for upstream actions**

Replace `_handle_upgrade_clicked`:
```python
    def _handle_upgrade_clicked(self, index: QModelIndex) -> None:
        row_idx = index.row()
        if row_idx >= len(self._display_items):
            return
        if self._display_items[row_idx]["type"] != _ITEM_RESOURCE:
            return
        resource = self._display_items[row_idx]["row"]
        name = resource["name"]

        if self.kind == "skills":
            upstream = self._upstreams.get(name, {})
            url = str(upstream.get("url") or "").strip()
            if not url:
                dialog = SetSkillUrlDialog(f"设置 URL：{name}", self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                url = dialog.url()
                if not url:
                    return
                self.set_url_requested.emit({"names": [name], "url": url})
                return
            update = self._update_results.get(name, {})
            if not update:
                self.check_upstream_requested.emit({"names": [name]})
                return
            has_update = bool(update.get("latestCommit")) and update.get("latestCommit") != update.get("installedCommit")
            if has_update:
                self.upgrade_upstream_requested.emit({"names": [name]})
                return

        if not self._is_upgradeable_row(resource):
            return
        targets = deepcopy(self.assignments.get(name, {}))
        if not self._has_assignments(targets):
            return
        self.sync_requested.emit(
            self.kind,
            {
                "action": "upgrade",
                "names": [name],
                "assignments": {name: targets},
            },
        )
```

**Step 7: Update `_emit_upgrade_all` for skills upstream**

Replace `_emit_upgrade_all`:
```python
    def _emit_upgrade_all(self) -> None:
        if self.kind == "skills":
            upstream_names = [
                name for name, upstream in self._upstreams.items()
                if upstream.get("url")
            ]
            if upstream_names:
                self.upgrade_upstream_requested.emit({"names": upstream_names})
                return
        names = self._upgradeable_names()
        assignments = self._build_upgrade_assignments(names)
        self.sync_requested.emit(
            self.kind,
            {
                "action": "upgrade",
                "names": names,
                "assignments": assignments,
            },
        )
```

**Step 8: Add upstream data methods**

Add these new methods:
```python
    def set_upstream_context(
        self,
        inventory: list[dict[str, object]],
        upstreams: dict[str, dict[str, object]],
    ) -> None:
        from copy import deepcopy as _dc
        self._upstream_inventory = _dc(inventory) if isinstance(inventory, list) else []
        self._upstreams = _dc(upstreams) if isinstance(upstreams, dict) else {}
        self._rebuild_table()

    def set_update_results(self, results: list[dict[str, object]]) -> None:
        self._update_results = {
            str(item.get("name")): deepcopy(item)
            for item in results
            if isinstance(item, dict)
        }
        self._rebuild_table()

    def _open_add_dialog(self) -> None:
        dialog = AddSkillFromUrlDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dialog.payload()
        if not payload["name"]:
            QMessageBox.warning(self, "新增失败", "请填写 Skill 名称。")
            return
        if not payload["url"]:
            QMessageBox.warning(self, "新增失败", "请填写 URL。")
            return
        self.add_skill_requested.emit(payload)

    def _open_set_url_dialog(self) -> None:
        names = self.get_selected_names()
        if not names:
            QMessageBox.warning(self, "设置失败", "请先选择 Skill。")
            return
        dialog = SetSkillUrlDialog(f"设置 URL（{len(names)} 个）", self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        url = dialog.url()
        if not url:
            QMessageBox.warning(self, "设置失败", "请填写 URL。")
            return
        self.set_url_requested.emit({"names": names, "url": url})

    def _emit_check(self) -> None:
        names = self.get_selected_names()
        self.check_upstream_requested.emit({"names": names})
```

**Step 9: Update `set_busy` to accept optional upstream_busy**

Replace `set_busy`:
```python
    def set_busy(self, rescan_busy: bool, sync_busy: bool, upstream_busy: bool = False) -> None:
        self.rescan_button.set_busy(rescan_busy)
        self.sync_button.set_busy(sync_busy)
        self.upgrade_button.set_busy(sync_busy or upstream_busy)
        self.remove_button.set_busy(sync_busy)
        if self.add_skill_button:
            self.add_skill_button.set_busy(upstream_busy)
        if self.set_url_button:
            self.set_url_button.set_busy(upstream_busy)
        if self.check_button:
            self.check_button.set_busy(upstream_busy)
```

**Step 10: Update toggle button hover color in `_build_expandable_name_cell`**

In the standalone function `_build_expandable_name_cell`, update the hardcoded hover color from `#f97316` (orange) to `#3b82f6` (blue):
```python
    toggle.setStyleSheet(
        "QPushButton { border: none; background: transparent;"
        " font-size: 10px; color: #6b7280; }"
        "QPushButton:hover { color: #3b82f6; }"
    )
```

**Step 11: Verify compilation**

Run: `python -m compileall python_app`
Expected: all files compile without error.

**Step 12: Run tests**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: some smoke tests may need adjustment — fix in Task 8.

**Step 13: Commit**

```bash
git add python_app/gui/main_window.py python_app/gui/pages/resource_page.py
git commit -m "feat: merge Skills Upstream into ResourcePage, redesign sidebar, remove outer ScrollArea"
```

---

## Task 7: Update Controller Signal Connections

**Files:**
- Modify: `python_app/controller.py:47-67` (`_connect_signals`)

**Step 1: Update `_connect_signals`**

The controller already connects `skill_add_requested`, `skill_set_url_requested`, `skill_check_requested`, `skill_upgrade_requested` from the window. These signals are still present on `MainWindow` and now route through `skills_page` instead of the removed `skill_upstream_page`. No changes needed to `controller.py` — the signal names on `MainWindow` haven't changed.

**Step 2: Verify compilation**

Run: `python -m compileall python_app`
Expected: all files compile without error.

**Step 3: Run full test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: PASS (or fix failures in Task 8).

**Step 4: Commit**

```bash
git add python_app/controller.py
git commit --allow-empty -m "chore: controller signal routing unchanged after upstream merge"
```

---

## Task 8: Update Smoke Tests and Delete Old Files

**Files:**
- Modify: `tests/test_gui_smoke.py`
- Delete: `python_app/gui/pages/skill_upstream_page.py`

**Step 1: Update smoke test imports**

In `test_gui_smoke.py`, the `MainWindow` import still works. No `SkillUpstreamPage` import exists in the test file, so no removal needed.

**Step 2: Fix test assertions for column indices if needed**

The table column structure is unchanged (still 12 columns: checkbox, name, type, 8 matrix, action). So column index assertions should still be correct.

However, `test_resource_page_shows_upgrade_when_partially_missing_with_existing_target` checks column 11 text — this still works since the ACTION_COLUMN index hasn't changed.

**Step 3: Add smoke test for skills upstream signals**

Add new test:
```python
    def test_skills_page_has_upstream_signals(self) -> None:
        page = ResourcePage("skills")
        self.assertTrue(hasattr(page, "add_skill_requested"))
        self.assertTrue(hasattr(page, "set_url_requested"))
        self.assertTrue(hasattr(page, "check_upstream_requested"))
        self.assertTrue(hasattr(page, "upgrade_upstream_requested"))
        self.assertIsNotNone(page.add_skill_button)
        self.assertIsNotNone(page.set_url_button)
        self.assertIsNotNone(page.check_button)

    def test_commands_page_has_no_upstream_buttons(self) -> None:
        page = ResourcePage("commands")
        self.assertIsNone(page.add_skill_button)
        self.assertIsNone(page.set_url_button)
        self.assertIsNone(page.check_button)
```

**Step 4: Add smoke test for main_window page count**

Add new test:
```python
    def test_main_window_has_7_pages(self) -> None:
        window = MainWindow()
        self.assertEqual(window.pages.count(), 7)
        self.assertFalse(hasattr(window, "skill_upstream_page"))
```

**Step 5: Run tests**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: all tests PASS.

**Step 6: Delete `skill_upstream_page.py`**

```bash
rm python_app/gui/pages/skill_upstream_page.py
```

Verify no imports remain:
Run: `rg "skill_upstream_page" python_app/`
Expected: no matches.

**Step 7: Verify compilation after delete**

Run: `python -m compileall python_app`
Expected: all files compile without error.

**Step 8: Commit**

```bash
git add tests/test_gui_smoke.py
git rm python_app/gui/pages/skill_upstream_page.py
git commit -m "test: update smoke tests for 7-page layout, delete skill_upstream_page"
```

---

## Task 9: Page-Specific Style Optimizations

**Files:**
- Modify: `python_app/gui/pages/overview_page.py`
- Modify: `python_app/gui/pages/config_page.py`
- Modify: `python_app/gui/pages/cleanup_page.py`
- Modify: `python_app/gui/pages/tools_page.py`
- Modify: `python_app/gui/pages/global_rule_page.py`

These are purely cosmetic adjustments. The new theme QSS handles most styling automatically. The changes below address layout-specific issues called out in the design spec.

**Step 1: Overview page — increase card spacing**

In `overview_page.py`, `_build_metric_strip`, change `setHorizontalSpacing(16)` to `setHorizontalSpacing(20)`:
```python
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)
```

**Step 2: Config page — tighten form alignment**

No structural changes needed. The new theme QSS already updates borders, inputs, and border-radius values. The form layout with `QFormLayout` and `AlignRight` label alignment is already correct per the design spec.

**Step 3: Cleanup page — no changes needed**

The cleanup page is already compact (85 lines). The new theme styles are sufficient.

**Step 4: Tools page — no changes needed**

The tools page card and table styles are driven by the theme QSS.

**Step 5: Global rule page — no changes needed**

The global rule page layout with splitter, target cards, and toolbar uses theme-driven styles.

**Step 6: Verify compilation**

Run: `python -m compileall python_app`
Expected: all files compile without error.

**Step 7: Commit**

```bash
git add python_app/gui/pages/overview_page.py
git commit -m "style: increase metric card spacing on overview page"
```

---

## Task 10: Final Verification

**Files:**
- None (verification only)

**Step 1: Full compilation check**

Run: `python -m compileall python_app`
Expected: all files compile without error.

**Step 2: Full test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: all tests PASS.

**Step 3: Verify no orphan imports**

Run: `rg "skill_upstream_page" python_app/`
Expected: no matches.

Run: `rg "SkillUpstreamPage" python_app/`
Expected: no matches.

Run: `rg "sidebarHero" python_app/`
Expected: no matches.

Run: `rg "Boss Console" python_app/`
Expected: no matches.

Run: `rg "Fira Sans" python_app/`
Expected: no matches (replaced with Segoe UI).

Run: `rg "Fira Code" python_app/`
Expected: no matches (replaced with Cascadia Code).

Run: `rg "#f97316" python_app/`
Expected: no matches (old orange accent removed).

**Step 4: Visual smoke test**

Run: `python -m python_app`
Expected: application launches with:
- Blue-white theme (no orange)
- Sidebar shows "AI Config Sync" title, 180px wide, 7 nav items
- No outer scrollbar on workspace
- Skills page has upstream buttons (新增 Skill, 设置 URL, 检查更新)
- Action column shows context-dependent text for skills
- All pages render without errors

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete frontend redesign — modern blue-white theme, merged Skills upstream, 7-page layout"
```
