import sys
from dataclasses import dataclass

from PySide6.QtWidgets import QApplication

from .controller import AppController
from .core.app_service import AppService, create_app_service
from .core.environment_service import assert_windows_host
from .gui.main_window import MainWindow
from .gui.theme import create_app_font


@dataclass(frozen=True)
class BootstrapBundle:
    app: QApplication
    controller: AppController
    window: MainWindow


def create_application(service: AppService | None = None, start_controller: bool = True) -> BootstrapBundle:
    assert_windows_host()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("AI Config Sync")
    app.setFont(create_app_font(10))
    window = MainWindow()
    controller = AppController(window, service or create_app_service())
    if start_controller:
        controller.start()
    return BootstrapBundle(app=app, controller=controller, window=window)


def run() -> int:
    bundle = create_application()
    bundle.window.show()
    return bundle.app.exec()
