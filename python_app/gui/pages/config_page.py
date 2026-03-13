from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.tool_definitions import TOOL_IDS
from ..dashboard import serialize
from ..widgets import ActionButton, CardFrame, layout_container


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
        layout.setSpacing(18)
        layout.addWidget(self._build_top_cards())
        layout.addWidget(self._build_target_stack())
        layout.addWidget(self._build_support_card())
        self.dirty_label = QLabel("")
        self.dirty_label.setObjectName("muted")
        layout.addWidget(self.dirty_label)
        layout.addStretch(1)

    def _build_top_cards(self) -> QWidget:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(self._build_base_card(), 0, 0)
        grid.addWidget(self._build_environment_card(), 0, 1)
        return layout_container(grid)

    def _build_base_card(self) -> QWidget:
        card = CardFrame("同步模式与源目录", "设置全局同步模式和 Skills / Commands 源目录。")
        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.sync_mode = QComboBox()
        self.sync_mode.addItems(("symlink", "copy"))
        self.skills_source = QLineEdit()
        self.commands_source = QLineEdit()
        form.addRow("Sync Mode", self.sync_mode)
        form.addRow("Skills Source", self.skills_source)
        form.addRow("Commands Source", self.commands_source)
        card.body_layout.addLayout(form)
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 6, 0, 0)
        button_row.setSpacing(12)
        self.reload_button = ActionButton("刷新 WSL", "secondary")
        self.save_button = ActionButton("保存配置", "primary")
        self.reload_button.clicked.connect(self.reload_requested.emit)
        self.save_button.clicked.connect(lambda: self.save_requested.emit(self.get_patch()))
        button_row.addStretch(1)
        button_row.addWidget(self.reload_button)
        button_row.addWidget(self.save_button)
        card.body_layout.addLayout(button_row)
        self._connect_dirty_signals([self.sync_mode, self.skills_source, self.commands_source])
        return card

    def _build_environment_card(self) -> QWidget:
        card = CardFrame("WSL 运行时", "自动检测发行版，WSL 同步开关在 Skills / Commands 页面设置。")
        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.wsl_distro = QComboBox()
        self.wsl_home = QLabel("未检测")
        self.wsl_home.setObjectName("muted")
        self.wsl_error = QLabel("")
        self.wsl_error.setObjectName("muted")
        self.wsl_error.setWordWrap(True)
        form.addRow("Distro", self.wsl_distro)
        form.addRow("Home", self.wsl_home)
        form.addRow("Error", self.wsl_error)
        card.body_layout.addLayout(form)
        self._connect_dirty_signals([self.wsl_distro])
        return card

    def _build_target_stack(self) -> QWidget:
        stack = QVBoxLayout()
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(16)
        stack.addWidget(self._build_target_matrix_card("windows", "Windows 目标路径"))
        stack.addWidget(self._build_target_matrix_card("wsl", "WSL 目标路径"))
        return layout_container(stack)

    def _build_target_matrix_card(self, environment_id: str, title: str) -> QWidget:
        detail = "Skills / Commands 按工具分别配置目标路径。"
        card = CardFrame(title, detail)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)
        self._add_target_group(grid, environment_id, "skills", 0)
        self._add_target_group(grid, environment_id, "commands", 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        card.body_layout.addLayout(grid)
        return card

    def _add_target_group(self, grid: QGridLayout, environment_id: str, kind: str, column: int) -> None:
        title = QLabel(kind.upper())
        title.setObjectName("eyebrow")
        grid.addWidget(title, 0, column, 1, 2)
        for row, tool_id in enumerate(TOOL_IDS, start=1):
            label = QLabel(tool_id.upper())
            label.setObjectName("formLabel")
            label.setFixedWidth(100)
            editor = QLineEdit()
            self._targets[(environment_id, kind, tool_id)] = editor
            editor.textChanged.connect(self._refresh_dirty)
            grid.addWidget(label, row, column)
            grid.addWidget(editor, row, column + 1)

    def _build_support_card(self) -> QWidget:
        card = CardFrame("命令目录结构", "控制 Commands 同步时是否保留上层目录结构。")
        self.default_support = QCheckBox("默认保留目录结构")
        self.default_support.stateChanged.connect(self._refresh_dirty)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)
        grid.addWidget(self.default_support, 0, 0, 1, 2)
        for tool_id in TOOL_IDS:
            checkbox = QCheckBox(f"{tool_id} 保留目录结构")
            checkbox.stateChanged.connect(self._refresh_dirty)
            self._tool_support[tool_id] = checkbox
        for index, (tool_id, checkbox) in enumerate(self._tool_support.items(), start=1):
            row = ((index - 1) // 2) + 1
            column = (index - 1) % 2
            grid.addWidget(checkbox, row, column)
        card.body_layout.addLayout(grid)
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
        self.wsl_distro.blockSignals(True)
        self.wsl_distro.clear()
        self.wsl_distro.addItem("")
        self.wsl_distro.addItems(wsl_runtime["distros"])
        self.wsl_distro.setCurrentText(wsl_runtime["selectedDistro"] or config["environments"]["wsl"]["selectedDistro"] or "")
        self.wsl_distro.blockSignals(False)
        self.wsl_home.setText(wsl_runtime["homeDir"] or "未检测")
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
                    "selectedDistro": self.wsl_distro.currentText() or None,
                    "targets": self._collect_targets("wsl"),
                },
            },
            "commandSubfolderSupport": {
                "default": self.default_support.isChecked(),
                "tools": {tool_id: checkbox.isChecked() for tool_id, checkbox in self._tool_support.items()},
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
            "environments": {
                "windows": {"targets": deepcopy(config["environments"]["windows"]["targets"])},
                "wsl": {
                    "selectedDistro": config["environments"]["wsl"]["selectedDistro"],
                    "targets": deepcopy(config["environments"]["wsl"]["targets"]),
                },
            },
            "commandSubfolderSupport": deepcopy(config["commandSubfolderSupport"]),
        }

    def _refresh_dirty(self) -> None:
        if not self._original_patch:
            self.dirty_label.setText("")
            return
        dirty = serialize(self.get_patch()) != serialize(self._original_patch)
        self.dirty_label.setText("有未保存的修改" if dirty else "配置已保存")
