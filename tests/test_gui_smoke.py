import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel

from python_app.gui.logo_matrix import LOGO_ACTIVE_ROLE, LOGO_TOOL_ROLE, ToolLogoDelegate
from python_app.gui.header_views import GroupedHeaderView
from python_app.gui.main_window import MainWindow
from python_app.gui.pages.global_rule_page import GlobalRulePage
from python_app.gui.pages.resource_page import ResourcePage


class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_instantiates(self) -> None:
        window = MainWindow()
        self.assertEqual(window.windowTitle(), "AI Config Sync")
        self.assertIsNotNone(window.pages)

    def test_resource_page_hides_tool_matrix_in_main_table(self) -> None:
        page = ResourcePage("commands")
        page.set_rows(
            [
                {
                    "name": "brainstorming.md",
                    "path": r"D:\wcs_project\ai-config-sync\commands\brainstorming.md",
                    "isDirectory": False,
                    "effectiveTargets": {},
                    "configuredTargets": {},
                    "entries": [],
                }
            ]
        )

        self.assertEqual(page.table.horizontalHeaderItem(1).text(), "名称")
        self.assertEqual(page.table.horizontalHeaderItem(2).text(), "类型")
        frozen_view = page.table.frozen_view()
        self.assertTrue(all(page.table.isColumnHidden(column) for column in range(3, 11)))
        self.assertTrue(all(not frozen_view.isColumnHidden(column) for column in range(3, 11)))
        self.assertEqual(frozen_view.horizontalHeader().minimumHeight(), 30)
        self.assertEqual(frozen_view.horizontalHeader().maximumHeight(), 30)

    def test_resource_page_uses_logo_matrix_items_and_click_toggles_assignment(self) -> None:
        page = ResourcePage("commands")
        captured: list[tuple[str, object]] = []
        page.sync_requested.connect(lambda kind, payload: captured.append((kind, payload)))
        page.set_rows(
            [
                {
                    "name": "brainstorming.md",
                    "path": r"D:\wcs_project\ai-config-sync\commands\brainstorming.md",
                    "isDirectory": False,
                    "effectiveTargets": {"windows": ["codex"]},
                    "configuredTargets": {"windows": ["codex"]},
                    "entries": [],
                }
            ]
        )

        item = page.table.item(0, 4)
        self.assertEqual(item.data(LOGO_TOOL_ROLE), "codex")
        self.assertTrue(item.data(LOGO_ACTIVE_ROLE))
        self.assertFalse(bool(item.flags() & Qt.ItemFlag.ItemIsUserCheckable))

        page._handle_matrix_clicked(page.table.model().index(0, 4))

        self.assertFalse(page.table.item(0, 4).data(LOGO_ACTIVE_ROLE))
        self.assertEqual(captured[0][0], "commands")
        self.assertEqual(captured[0][1]["action"], "remove")

    def test_resource_page_header_checkbox_selects_current_page_rows(self) -> None:
        page = ResourcePage("commands")
        page.set_rows(
            [
                {
                    "name": "a.md",
                    "path": r"D:\wcs_project\ai-config-sync\commands\a.md",
                    "isDirectory": False,
                    "effectiveTargets": {},
                    "configuredTargets": {},
                    "entries": [],
                },
                {
                    "name": "b.md",
                    "path": r"D:\wcs_project\ai-config-sync\commands\b.md",
                    "isDirectory": False,
                    "effectiveTargets": {},
                    "configuredTargets": {},
                    "entries": [],
                },
            ]
        )

        header = page.table.horizontalHeader()
        self.assertIsInstance(header, GroupedHeaderView)

        header.checkbox_state_changed.emit(0, Qt.CheckState.Checked.value)
        self.assertEqual(page.get_selected_names(), ["a.md", "b.md"])
        self.assertTrue(page.table.cellWidget(0, 0).findChild(QCheckBox).isChecked())
        self.assertTrue(page.table.cellWidget(1, 0).findChild(QCheckBox).isChecked())

        header.checkbox_state_changed.emit(0, Qt.CheckState.Unchecked.value)
        self.assertEqual(page.get_selected_names(), [])
        self.assertFalse(page.table.cellWidget(0, 0).findChild(QCheckBox).isChecked())
        self.assertFalse(page.table.cellWidget(1, 0).findChild(QCheckBox).isChecked())

    def test_logo_delegate_uses_white_background_for_all_active_states(self) -> None:
        delegate = ToolLogoDelegate()

        healthy_colors = delegate._badge_colors("healthy", True)
        missing_colors = delegate._badge_colors("missing", True)
        conflict_colors = delegate._badge_colors("conflict", True)

        self.assertEqual(healthy_colors[1], "#ffffff")
        self.assertEqual(missing_colors[1], "#ffffff")
        self.assertEqual(conflict_colors[1], "#ffffff")

    def test_resource_page_pager_shows_installed_counts_for_win_and_wsl(self) -> None:
        page = ResourcePage("skills")
        page.set_rows(
            [
                {
                    "name": "a",
                    "path": r"D:\wcs_project\ai-config-sync\skills\a",
                    "isDirectory": True,
                    "effectiveTargets": {"windows": ["claude", "codex"], "wsl": ["codex"]},
                    "configuredTargets": {},
                    "entries": [],
                },
                {
                    "name": "b",
                    "path": r"D:\wcs_project\ai-config-sync\skills\b",
                    "isDirectory": True,
                    "effectiveTargets": {"windows": ["codex"], "wsl": ["codex", "gemini"]},
                    "configuredTargets": {},
                    "entries": [],
                },
            ]
        )

        labels = {label.text() for label in page.pager.findChildren(QLabel)}
        self.assertIn("WIN 已安装", labels)
        self.assertIn("WSL 已安装", labels)
        self.assertIn("Claude: 1", labels)
        self.assertIn("Codex: 2", labels)
        self.assertIn("Gemini: 1", labels)

    def test_global_rule_page_disables_sync_when_profile_dirty(self) -> None:
        page = GlobalRulePage()
        page.set_context(
            {
                "profiles": [
                    {
                        "id": "rule-1",
                        "name": "规则1",
                        "file": "rule-1.md",
                        "updatedAt": "2026-03-20T00:00:00",
                        "content": "# rule",
                    }
                ],
                "assignments": {
                    "windows": {"claude": "rule-1", "codex": None, "gemini": None},
                    "wsl": {"claude": None, "codex": None, "gemini": None},
                },
            },
            [
                {
                    "environmentId": "windows",
                    "toolId": "claude",
                    "targetFilePath": r"C:\Users\Administrator\.claude\CLAUDE.md",
                    "profileId": "rule-1",
                    "profileName": "规则1",
                    "state": "healthy",
                    "message": "已同步",
                },
                {
                    "environmentId": "windows",
                    "toolId": "codex",
                    "targetFilePath": r"C:\Users\Administrator\.codex\AGENTS.md",
                    "profileId": None,
                    "profileName": None,
                    "state": "idle",
                    "message": "未分配规则版本",
                },
                {
                    "environmentId": "windows",
                    "toolId": "gemini",
                    "targetFilePath": r"C:\Users\Administrator\.gemini\GEMINI.md",
                    "profileId": None,
                    "profileName": None,
                    "state": "idle",
                    "message": "未分配规则版本",
                },
                {
                    "environmentId": "wsl",
                    "toolId": "claude",
                    "targetFilePath": None,
                    "profileId": None,
                    "profileName": None,
                    "state": "environment_error",
                    "message": "未发现 WSL 发行版",
                },
                {
                    "environmentId": "wsl",
                    "toolId": "codex",
                    "targetFilePath": None,
                    "profileId": None,
                    "profileName": None,
                    "state": "environment_error",
                    "message": "未发现 WSL 发行版",
                },
                {
                    "environmentId": "wsl",
                    "toolId": "gemini",
                    "targetFilePath": None,
                    "profileId": None,
                    "profileName": None,
                    "state": "environment_error",
                    "message": "未发现 WSL 发行版",
                },
            ],
        )

        page.name_input.setText("规则1-改")

        self.assertTrue(page.sync_all_button.isEnabled() is False)
        self.assertIn("规则版本有未保存修改", page.status_label.text())


if __name__ == "__main__":
    unittest.main()
