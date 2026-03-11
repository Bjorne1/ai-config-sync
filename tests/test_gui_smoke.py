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

    def test_resource_page_uses_compact_status_text_with_full_tooltip(self) -> None:
        page = ResourcePage("commands")
        page.set_rows(
            [
                {
                    "name": "brainstorming.md",
                    "path": r"D:\wcs_project\ai-config-sync\commands\brainstorming.md",
                    "isDirectory": False,
                    "summaryMessage": "部分目标存在冲突",
                    "effectiveTargets": {},
                    "configuredTargets": {},
                    "entries": [
                        {"environmentId": "windows", "toolId": "claude", "state": "conflict"},
                        {"environmentId": "windows", "toolId": "codex", "state": "conflict"},
                        {"environmentId": "wsl", "toolId": "gemini", "state": "missing"},
                    ],
                }
            ]
        )

        status_item = page.table.item(0, 5)
        self.assertEqual(status_item.text(), "存在冲突 2 · 目标缺失 1")
        self.assertEqual(
            status_item.toolTip(),
            "windows/claude: 存在冲突 | windows/codex: 存在冲突 | wsl/gemini: 目标缺失",
        )
        frozen_view = page.table.frozen_view()
        self.assertTrue(all(page.table.isColumnHidden(column) for column in range(6, 14)))
        self.assertTrue(all(not frozen_view.isColumnHidden(column) for column in range(6, 14)))


if __name__ == "__main__":
    unittest.main()
