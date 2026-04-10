import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QMessageBox

from python_app.controller import AppController
from python_app.gui.logo_matrix import LOGO_ACTIVE_ROLE, LOGO_TOOL_ROLE, ToolLogoDelegate
from python_app.gui.header_views import GroupedHeaderView
from python_app.gui.main_window import MainWindow
from python_app.gui.pages.global_rule_page import GlobalRulePage
from python_app.gui.pages.resource_page import ResourcePage
from python_app.gui.pages.workflow_page import WorkflowPage


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
                    "detectedTargets": {"windows": ["codex"]},
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

    def test_resource_page_dims_missing_target_even_when_assignment_exists(self) -> None:
        page = ResourcePage("commands")
        page.set_rows(
            [
                {
                    "name": "brainstorming.md",
                    "path": r"D:\wcs_project\ai-config-sync\commands\brainstorming.md",
                    "isDirectory": False,
                    "effectiveTargets": {"windows": ["codex"]},
                    "configuredTargets": {"windows": ["codex"]},
                    "detectedTargets": {},
                    "entries": [
                        {
                            "environmentId": "windows",
                            "toolId": "codex",
                            "state": "missing",
                            "message": "目标缺失",
                            "targetExists": False,
                        }
                    ],
                }
            ]
        )

        item = page.table.item(0, 4)
        self.assertFalse(item.data(LOGO_ACTIVE_ROLE))
        self.assertIn("目标缺失", item.toolTip())
        self.assertEqual(page.table.item(0, 11).text(), "")

    def test_resource_page_keeps_source_missing_target_dark_when_target_absent(self) -> None:
        page = ResourcePage("skills")
        page.set_rows(
            [
                {
                    "name": "demo-skill",
                    "path": r"D:\wcs_project\ai-config-sync\skills\demo-skill",
                    "isDirectory": True,
                    "effectiveTargets": {"windows": ["claude"]},
                    "configuredTargets": {"windows": ["claude"]},
                    "detectedTargets": {},
                    "entries": [
                        {
                            "environmentId": "windows",
                            "toolId": "claude",
                            "state": "source_missing",
                            "message": "源文件不存在",
                            "targetExists": False,
                        }
                    ],
                }
            ]
        )

        item = page.table.item(0, 3)
        self.assertFalse(item.data(LOGO_ACTIVE_ROLE))
        self.assertIn("源文件不存在", item.toolTip())

    def test_resource_page_shows_upgrade_when_partially_missing_with_existing_target(self) -> None:
        page = ResourcePage("skills")
        page.set_rows(
            [
                {
                    "name": "demo-skill",
                    "path": r"D:\wcs_project\ai-config-sync\skills\demo-skill",
                    "isDirectory": True,
                    "effectiveTargets": {"windows": ["claude", "codex"]},
                    "configuredTargets": {"windows": ["claude", "codex"]},
                    "detectedTargets": {"windows": ["claude"]},
                    "entries": [
                        {
                            "environmentId": "windows",
                            "toolId": "claude",
                            "state": "healthy",
                            "message": "已同步",
                            "targetExists": True,
                        },
                        {
                            "environmentId": "windows",
                            "toolId": "codex",
                            "state": "missing",
                            "message": "目标缺失",
                            "targetExists": False,
                        },
                    ],
                }
            ]
        )

        page.set_upstream_context(
            [{"name": "demo-skill", "path": r"D:\wcs_project\ai-config-sync\skills\demo-skill"}],
            {"demo-skill": {"url": "https://github.com/test/repo", "installedCommit": "abc123"}},
        )
        page.set_update_results([
            {"name": "demo-skill", "installedCommit": "abc123", "latestCommit": "abc123"},
        ])

        self.assertEqual(page.table.item(0, 11).text(), "升级")

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

    def test_main_window_has_7_pages(self) -> None:
        window = MainWindow()
        self.assertEqual(window.pages.count(), 8)
        self.assertFalse(hasattr(window, "skill_upstream_page"))

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

    def test_global_rule_page_keeps_sync_enabled_and_sends_assignments_when_dirty(self) -> None:
        page = GlobalRulePage()
        captured: list[object] = []
        page.sync_requested.connect(captured.append)
        statuses = [
            {
                "environmentId": env,
                "toolId": tool,
                "targetFilePath": None,
                "profileId": None,
                "profileName": None,
                "state": "idle",
                "message": "未分配规则版本",
            }
            for env in ("windows", "wsl")
            for tool in ("claude", "codex", "gemini")
        ]
        statuses[0].update(
            targetFilePath=r"C:\Users\Administrator\.claude\CLAUDE.md",
            profileId="rule-1",
            profileName="规则1",
            state="healthy",
            message="已同步",
        )
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
            statuses,
        )
        self.assertTrue(page.sync_all_button.isEnabled())

        page._handle_assignment_changed("windows", "codex", "rule-1")

        self.assertTrue(page.sync_all_button.isEnabled())
        self.assertIn("同步时会自动保存", page.status_label.text())

        page._emit_sync_one("windows", "codex")

        self.assertEqual(
            captured[0],
            {
                "targets": [{"environmentId": "windows", "toolId": "codex"}],
                "assignments": {
                    "windows": {"claude": "rule-1", "codex": "rule-1", "gemini": None},
                    "wsl": {"claude": None, "codex": None, "gemini": None},
                },
            },
        )

    def test_workflow_page_formats_omx_version_and_hides_skills_buttons(self) -> None:
        page = WorkflowPage()
        page.set_context(
            [
                {
                    "workflowId": "oh-my-codex",
                    "label": "oh-my-codex",
                    "description": "test",
                    "repoUrl": "https://github.com/Bjorne1/oh-my-codex",
                    "targets": {
                        "windows:codex": {
                            "available": True,
                            "installed": True,
                            "enabled": True,
                            "version": "0.12.4",
                            "installedCommit": "abcdef123456",
                            "skillsLinkable": False,
                        }
                    },
                }
            ]
        )

        card = page._workflow_cards["oh-my-codex"]
        row = card._target_rows["windows:codex"]

        self.assertEqual(row._version_label.text(), "v0.12.4 · abcdef12")
        self.assertEqual([button.text() for button in row._buttons], ["升级", "禁用", "卸载"])

    def test_controller_converts_omx_confirm_yes_to_force_action(self) -> None:
        window = MainWindow()
        service = mock.Mock()
        controller = AppController(window, service=service)
        window.snapshot = {
            "workflowStatuses": [
                {
                    "workflowId": "oh-my-codex",
                    "targets": {
                        "windows:codex": {
                            "enabled": False,
                            "agentsFileExists": True,
                            "agentsFilePath": r"C:\Users\me\.codex\AGENTS.md",
                        }
                    },
                }
            ]
        }

        with mock.patch(
            "python_app.controller.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            action = controller._resolve_workflow_action("oh-my-codex", "windows:codex", "install")

        self.assertEqual(action, "install_force")

    def test_controller_converts_omx_confirm_no_to_no_force_action(self) -> None:
        window = MainWindow()
        service = mock.Mock()
        controller = AppController(window, service=service)
        window.snapshot = {
            "workflowStatuses": [
                {
                    "workflowId": "oh-my-codex",
                    "targets": {
                        "windows:codex": {
                            "enabled": True,
                            "agentsFileExists": True,
                            "agentsFilePath": r"C:\Users\me\.codex\AGENTS.md",
                        }
                    },
                }
            ]
        }

        with mock.patch(
            "python_app.controller.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No,
        ):
            action = controller._resolve_workflow_action("oh-my-codex", "windows:codex", "upgrade")

        self.assertEqual(action, "upgrade_no_force")

    def test_controller_cancels_omx_action_when_prompt_cancelled(self) -> None:
        window = MainWindow()
        service = mock.Mock()
        controller = AppController(window, service=service)
        window.snapshot = {
            "workflowStatuses": [
                {
                    "workflowId": "oh-my-codex",
                    "targets": {
                        "windows:codex": {
                            "enabled": False,
                            "agentsFileExists": True,
                            "agentsFilePath": r"C:\Users\me\.codex\AGENTS.md",
                        }
                    },
                }
            ]
        }

        with mock.patch(
            "python_app.controller.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Cancel,
        ):
            action = controller._resolve_workflow_action("oh-my-codex", "windows:codex", "enable")

        self.assertIsNone(action)


if __name__ == "__main__":
    unittest.main()
