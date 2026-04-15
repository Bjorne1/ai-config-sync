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
from ...core.github_skill_upstream import infer_skill_name_from_github_url

_DIALOG_MIN_WIDTH = 640
_DIALOG_MIN_HEIGHT = 220


class AddSkillFromUrlDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新增 Skill")
        self.setModal(True)
        self.setMinimumSize(_DIALOG_MIN_WIDTH, _DIALOG_MIN_HEIGHT)
        self.name_input = QLineEdit()
        self.url_input = QLineEdit()
        self._last_suggested_name = ""
        self.url_input.setPlaceholderText("https://github.com/<owner>/<repo>/tree/<ref>/<path> 或 .../blob/<ref>/SKILL.md")
        self.url_input.textChanged.connect(self._sync_name_from_url)
        self._hint = QLabel("URL 可填 skills 父目录、具体 skill 目录，或直接指向仓库内的 SKILL.md；单文件会按仓库名建目录。")
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

    def _sync_name_from_url(self, text: str) -> None:
        current = self.name_input.text().strip()
        suggested = infer_skill_name_from_github_url(text) or ""
        if suggested:
            if not current or current == self._last_suggested_name:
                self.name_input.setText(suggested)
            self._last_suggested_name = suggested
            return
        if current == self._last_suggested_name:
            self.name_input.clear()
        self._last_suggested_name = ""

    def payload(self) -> dict[str, str]:
        url = self.url_input.text().strip()
        name = self.name_input.text().strip() or infer_skill_name_from_github_url(url) or ""
        return {"name": name, "url": url}


class SetSkillUrlDialog(QDialog):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(_DIALOG_MIN_WIDTH, _DIALOG_MIN_HEIGHT)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://github.com/<owner>/<repo>/tree/<ref>/<path> 或 .../blob/<ref>/SKILL.md")
        self._hint = QLabel(
            "目录 URL 会按名称自动拼接子路径；单文件 URL 只能绑定同名 skill。例如填 .../tree/main/skills，docx 和 pdf 会分别绑定到 .../skills/docx 和 .../skills/pdf。"
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
