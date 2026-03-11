from copy import deepcopy

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.tool_definitions import TOOL_IDS
from ..dashboard import serialize
from ..widgets import ActionButton, CardFrame, HeaderBlock


class ConfigPage(QWidget):
    reload_requested = Signal()
    save_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._targets: dict[tuple[str, str, str], QLineEdit] = {}
        self._tool_support: dict[str, QCheckBox] = {}
        self._original_patch: dict[str, object] | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(HeaderBlock("05 / Config", "配置矩阵", "修改同步模式、源目录、WSL 和目标路径，保存后由外部控制器提交。"))
        layout.addWidget(self._build_base_card())
        layout.addWidget(self._build_environment_card())
        layout.addLayout(self._build_target_cards())
        layout.addWidget(self._build_support_card())
        self.dirty_label = QLabel("")
        self.dirty_label.setObjectName("muted")
        layout.addWidget(self.dirty_label)

    def _build_base_card(self) -> QWidget:
        card = CardFrame("同步模式与源目录")
        form = QFormLayout()
        self.sync_mode = QComboBox()
        self.sync_mode.addItems(("symlink", "copy"))
        self.skills_source = QLineEdit()
        self.commands_source = QLineEdit()
        form.addRow("Sync Mode", self.sync_mode)
        form.addRow("Skills Source", self.skills_source)
        form.addRow("Commands Source", self.commands_source)
        card.body_layout.addLayout(form)
        self.reload_button = ActionButton("重载 WSL 列表", "secondary")
        self.save_button = ActionButton("保存配置", "primary")
        self.reload_button.clicked.connect(self.reload_requested.emit)
        self.save_button.clicked.connect(lambda: self.save_requested.emit(self.get_patch()))
        card.body_layout.addWidget(self.reload_button)
        card.body_layout.addWidget(self.save_button)
        self._connect_dirty_signals([self.sync_mode, self.skills_source, self.commands_source])
        return card

    def _build_environment_card(self) -> QWidget:
        card = CardFrame("WSL 运行时")
        form = QFormLayout()
        self.wsl_enabled = QCheckBox("启用 WSL 同步")
        self.wsl_distro = QComboBox()
        self.wsl_home = QLabel("未解析")
        self.wsl_home.setObjectName("muted")
        self.wsl_error = QLabel("")
        self.wsl_error.setObjectName("muted")
        form.addRow("WSL", self.wsl_enabled)
        form.addRow("Distro", self.wsl_distro)
        form.addRow("Home", self.wsl_home)
        form.addRow("Error", self.wsl_error)
        card.body_layout.addLayout(form)
        self._connect_dirty_signals([self.wsl_enabled, self.wsl_distro])
        return card

    def _build_target_cards(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setSpacing(12)
        cards = [
            ("windows", "skills", "Windows / Skills"),
            ("windows", "commands", "Windows / Commands"),
            ("wsl", "skills", "WSL / Skills"),
            ("wsl", "commands", "WSL / Commands"),
        ]
        for index, (environment_id, kind, title) in enumerate(cards):
            card = CardFrame(title)
            form = QFormLayout()
            for tool_id in TOOL_IDS:
                editor = QLineEdit()
                self._targets[(environment_id, kind, tool_id)] = editor
                editor.textChanged.connect(self._refresh_dirty)
                form.addRow(tool_id.upper(), editor)
            card.body_layout.addLayout(form)
            layout.addWidget(card, index // 2, index % 2)
        return layout

    def _build_support_card(self) -> QWidget:
        card = CardFrame("Command Folder Support")
        self.default_support = QCheckBox("默认保留目录")
        self.default_support.stateChanged.connect(self._refresh_dirty)
        card.body_layout.addWidget(self.default_support)
        for tool_id in TOOL_IDS:
            checkbox = QCheckBox(f"{tool_id} 保留目录")
            checkbox.stateChanged.connect(self._refresh_dirty)
            card.body_layout.addWidget(checkbox)
            self._tool_support[tool_id] = checkbox
        return card

    def _connect_dirty_signals(self, widgets: list[QWidget]) -> None:
        for widget in widgets:
            signal = getattr(widget, "textChanged", None) or getattr(widget, "currentTextChanged", None)
            if signal:
                signal.connect(self._refresh_dirty)
            if hasattr(widget, "stateChanged"):
                widget.stateChanged.connect(self._refresh_dirty)

    def set_context(self, config: dict[str, object], wsl_runtime: dict[str, object]) -> None:
        self._original_patch = self._patch_from_config(config)
        self.sync_mode.setCurrentText(config["syncMode"])
        self.skills_source.setText(config["sourceDirs"]["skills"])
        self.commands_source.setText(config["sourceDirs"]["commands"])
        self.wsl_enabled.setChecked(config["environments"]["wsl"]["enabled"])
        self.wsl_distro.blockSignals(True)
        self.wsl_distro.clear()
        self.wsl_distro.addItem("")
        self.wsl_distro.addItems(wsl_runtime["distros"])
        self.wsl_distro.setCurrentText(config["environments"]["wsl"]["selectedDistro"] or "")
        self.wsl_distro.blockSignals(False)
        self.wsl_home.setText(wsl_runtime["homeDir"] or "未解析")
        self.wsl_error.setText(wsl_runtime["error"] or "")
        self._fill_targets(config)
        self.default_support.setChecked(config["commandSubfolderSupport"]["default"])
        for tool_id, checkbox in self._tool_support.items():
            checkbox.setChecked(bool(config["commandSubfolderSupport"]["tools"].get(tool_id)))
        self._refresh_dirty()

    def _fill_targets(self, config: dict[str, object]) -> None:
        for environment_id in ("windows", "wsl"):
            for kind in ("skills", "commands"):
                for tool_id in TOOL_IDS:
                    editor = self._targets[(environment_id, kind, tool_id)]
                    editor.setText(config["environments"][environment_id]["targets"][kind][tool_id])

    def get_patch(self) -> dict[str, object]:
        return {
            "syncMode": self.sync_mode.currentText(),
            "sourceDirs": {
                "skills": self.skills_source.text().strip(),
                "commands": self.commands_source.text().strip(),
            },
            "environments": {
                "windows": {"targets": self._collect_targets("windows")},
                "wsl": {
                    "enabled": self.wsl_enabled.isChecked(),
                    "selectedDistro": self.wsl_distro.currentText() or None,
                    "targets": self._collect_targets("wsl"),
                },
            },
            "commandSubfolderSupport": {
                "default": self.default_support.isChecked(),
                "tools": {
                    tool_id: checkbox.isChecked()
                    for tool_id, checkbox in self._tool_support.items()
                },
            },
        }

    def _collect_targets(self, environment_id: str) -> dict[str, dict[str, str]]:
        return {
            kind: {
                tool_id: self._targets[(environment_id, kind, tool_id)].text().strip()
                for tool_id in TOOL_IDS
            }
            for kind in ("skills", "commands")
        }

    def set_busy(self, reload_busy: bool, save_busy: bool) -> None:
        self.reload_button.set_busy(reload_busy)
        self.save_button.set_busy(save_busy)

    def _patch_from_config(self, config: dict[str, object]) -> dict[str, object]:
        return {
            "syncMode": config["syncMode"],
            "sourceDirs": deepcopy(config["sourceDirs"]),
            "environments": deepcopy(config["environments"]),
            "commandSubfolderSupport": deepcopy(config["commandSubfolderSupport"]),
        }

    def _refresh_dirty(self) -> None:
        if not self._original_patch:
            self.dirty_label.setText("")
            return
        dirty = serialize(self.get_patch()) != serialize(self._original_patch)
        self.dirty_label.setText("存在未保存配置改动。" if dirty else "配置已同步。")
