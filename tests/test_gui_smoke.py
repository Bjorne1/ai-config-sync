import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from python_app.gui.logo_matrix import LOGO_ACTIVE_ROLE, LOGO_TOOL_ROLE, ToolLogoDelegate
from python_app.gui.main_window import MainWindow
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

    def test_logo_delegate_uses_white_background_for_all_active_states(self) -> None:
        delegate = ToolLogoDelegate()

        healthy_colors = delegate._badge_colors("healthy", True)
        missing_colors = delegate._badge_colors("missing", True)
        conflict_colors = delegate._badge_colors("conflict", True)

        self.assertEqual(healthy_colors[1], "#ffffff")
        self.assertEqual(missing_colors[1], "#ffffff")
        self.assertEqual(conflict_colors[1], "#ffffff")


if __name__ == "__main__":
    unittest.main()
