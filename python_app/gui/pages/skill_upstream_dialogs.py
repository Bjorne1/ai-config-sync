from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

_DIALOG_MIN_WIDTH = 640
_DIALOG_MIN_HEIGHT = 220


class AddSkillFromUrlDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新增线上 Skill")
        self.setModal(True)
        self.setMinimumSize(_DIALOG_MIN_WIDTH, _DIALOG_MIN_HEIGHT)
        self.name_input = QLineEdit()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://github.com/<owner>/<repo>/tree/<ref>/<path>")
        self._hint = QLabel("提示：URL 可填 skills 父目录或具体 skill 目录，程序会按 Skill 名称自动匹配。")
        self._hint.setObjectName("muted")
        self._hint.setWordWrap(True)
        self._hint.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Skill 名称", self.name_input)
        form.addRow("更新 URL", self.url_input)
        layout.addLayout(form)
        layout.addWidget(self._hint)
        layout.addWidget(buttons)

    def payload(self) -> dict[str, str]:
        return {"name": self.name_input.text().strip(), "url": self.url_input.text().strip()}


class SetSkillUrlDialog(QDialog):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(_DIALOG_MIN_WIDTH, _DIALOG_MIN_HEIGHT)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://github.com/<owner>/<repo>/tree/<ref>/<path>")
        self._hint = QLabel(
            "会按 Skill 名称自动拼接子路径，例如填入 .../tree/main/skills，docx/pdf 会分别绑定到 .../skills/docx 与 .../skills/pdf。"
        )
        self._hint.setObjectName("muted")
        self._hint.setWordWrap(True)
        self._hint.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("更新 URL", self.url_input)
        layout.addLayout(form)
        layout.addWidget(self._hint)
        layout.addWidget(buttons)

    def url(self) -> str:
        return self.url_input.text().strip()

