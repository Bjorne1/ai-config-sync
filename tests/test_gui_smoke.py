import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

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


if __name__ == "__main__":
    unittest.main()
