import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from python_app.gui.main_window import MainWindow


class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_instantiates(self) -> None:
        window = MainWindow()
        self.assertEqual(window.windowTitle(), "AI Config Sync")
        self.assertIsNotNone(window.pages)


if __name__ == "__main__":
    unittest.main()
