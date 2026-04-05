import os
import sys
from ctypes import windll
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .controller import AppController
from .core.app_service import AppService, create_app_service
from .core.environment_service import assert_windows_host
from .gui.main_window import MainWindow
from .gui.theme import create_app_font

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
APP_USER_MODEL_ID = "WCS.AIConfigSync.Desktop"


@dataclass(frozen=True)
class BootstrapBundle:
    app: QApplication
    controller: AppController
    window: MainWindow


def app_icon_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "app_icon.png"


def set_app_user_model_id() -> None:
    result = windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    if result != 0:
        raise OSError(f"SetCurrentProcessExplicitAppUserModelID failed: {result}")


def create_application(service: AppService | None = None, start_controller: bool = True) -> BootstrapBundle:
    assert_windows_host()
    set_app_user_model_id()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("AI Config Sync")
    app.setFont(create_app_font(10))
    icon = QIcon(str(app_icon_path()))
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    controller = AppController(window, service or create_app_service())
    if start_controller:
        controller.start()
    return BootstrapBundle(app=app, controller=controller, window=window)


def run() -> int:
    bundle = create_application()
    bundle.window.show()
    return bundle.app.exec()
