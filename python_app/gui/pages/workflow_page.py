from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..widgets import ActionButton, BadgeLabel, CardFrame


ENVIRONMENT_LABELS = {"windows": "Windows", "wsl": "WSL"}
TOOL_LABELS = {"claude": "Claude Code", "codex": "Codex"}

STATE_MAP = {
    "enabled": ("已启用", "healthy"),
    "disabled": ("已禁用", "outdated"),
    "not_installed": ("未安装", "idle"),
    "unavailable": ("不可用", "tool_unavailable"),
    "error": ("异常", "environment_error"),
}


def _target_state(target: dict[str, object]) -> str:
    if target.get("error"):
        if "目录不存在" in str(target["error"]):
            return "unavailable"
        return "error"
    if not target.get("available"):
        return "unavailable"
    if not target.get("installed"):
        return "not_installed"
    if target.get("enabled"):
        return "enabled"
    return "disabled"


class WorkflowTargetRow(QWidget):
    action_requested = Signal(str)

    def __init__(
        self,
        target_key: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._target_key = target_key
        self._buttons: list[ActionButton] = []
        parts = target_key.split(":", 1)
        env_label = ENVIRONMENT_LABELS.get(parts[0], parts[0]) if len(parts) == 2 else target_key
        tool_label = TOOL_LABELS.get(parts[1], parts[1]) if len(parts) == 2 else ""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)
        self._label = QLabel(f"{env_label} / {tool_label}")
        self._label.setMinimumWidth(140)
        self._badge = BadgeLabel("--", "idle")
        self._badge.setMinimumWidth(72)
        self._version_label = QLabel("")
        self._version_label.setObjectName("muted")
        self._version_label.setMinimumWidth(80)
        self._error_label = QLabel("")
        self._error_label.setObjectName("muted")
        self._error_label.setWordWrap(True)
        self._button_container = QWidget()
        self._button_layout = QHBoxLayout(self._button_container)
        self._button_layout.setContentsMargins(0, 0, 0, 0)
        self._button_layout.setSpacing(8)
        layout.addWidget(self._label)
        layout.addWidget(self._badge)
        layout.addWidget(self._version_label)
        layout.addWidget(self._error_label, 1)
        layout.addWidget(self._button_container)

    def set_context(self, target: dict[str, object]) -> None:
        state = _target_state(target)
        label, badge_state = STATE_MAP.get(state, STATE_MAP["error"])
        self._badge.setText(label)
        self._badge.set_state(badge_state)
        version = target.get("version")
        self._version_label.setText(f"v{version}" if version else "")
        error = target.get("error")
        self._error_label.setText(str(error) if error and state in ("error", "unavailable") else "")
        self._rebuild_buttons(state, target)

    def set_busy(self, busy: bool) -> None:
        for button in self._buttons:
            button.set_busy(busy)

    def _rebuild_buttons(self, state: str, target: dict[str, object]) -> None:
        for btn in self._buttons:
            btn.setParent(None)
            btn.deleteLater()
        self._buttons.clear()
        skills_linkable = bool(target.get("skillsLinkable"))
        skills_linked = bool(target.get("skillsLinked"))
        if state == "not_installed":
            self._add_button("安装", "primary", "install")
        elif state == "enabled":
            self._add_button("升级", "secondary", "upgrade")
            if skills_linkable:
                if skills_linked:
                    self._add_button("取消链接Skills", "secondary", "unlink_skills")
                else:
                    self._add_button("链接Skills", "secondary", "link_skills")
            self._add_button("禁用", "secondary", "disable")
            self._add_button("卸载", "danger", "uninstall")
        elif state == "disabled":
            self._add_button("升级", "secondary", "upgrade")
            if skills_linkable:
                if skills_linked:
                    self._add_button("取消链接Skills", "secondary", "unlink_skills")
                else:
                    self._add_button("链接Skills", "secondary", "link_skills")
            self._add_button("启用", "primary", "enable")
            self._add_button("卸载", "danger", "uninstall")

    def _add_button(self, label: str, variant: str, action: str) -> None:
        button = ActionButton(label, variant)
        button.clicked.connect(lambda _=False, a=action: self.action_requested.emit(a))
        self._button_layout.addWidget(button)
        self._buttons.append(button)


class WorkflowCard(CardFrame):
    action_requested = Signal(str, str)

    def __init__(
        self,
        workflow_id: str,
        label: str,
        description: str,
        repo_url: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(label, description, parent)
        self._workflow_id = workflow_id
        self._target_rows: dict[str, WorkflowTargetRow] = {}
        url_label = QLabel(f'<a href="{repo_url}">{repo_url}</a>')
        url_label.setOpenExternalLinks(True)
        url_label.setObjectName("muted")
        self.body_layout.addWidget(url_label)
        self._targets_container = QVBoxLayout()
        self._targets_container.setSpacing(2)
        self.body_layout.addLayout(self._targets_container)

    def set_targets(self, targets: dict[str, dict[str, object]]) -> None:
        for target_key, target_data in sorted(targets.items()):
            row = self._target_rows.get(target_key)
            if row is None:
                row = WorkflowTargetRow(target_key)
                row.action_requested.connect(
                    lambda action, tk=target_key: self.action_requested.emit(tk, action),
                )
                self._targets_container.addWidget(row)
                self._target_rows[target_key] = row
            row.set_context(target_data)

    def set_busy(self, busy_targets: set[str]) -> None:
        for target_key, row in self._target_rows.items():
            row.set_busy(target_key in busy_targets)


class WorkflowPage(QWidget):
    refresh_requested = Signal()
    workflow_action_requested = Signal(str, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._workflow_cards: dict[str, WorkflowCard] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        toolbar = self._build_toolbar()
        outer.addWidget(toolbar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 12, 0, 0)
        self._content_layout.setSpacing(18)
        self._content_layout.addStretch(1)
        scroll.setWidget(self._content)
        outer.addWidget(scroll, 1)

    def _build_toolbar(self) -> QWidget:
        card = CardFrame("工作流", "管理 AI 工具的工作流插件（安装、启用、禁用、卸载）。")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self._status_label = QLabel("正在加载…")
        self._status_label.setObjectName("muted")
        self._status_label.setWordWrap(True)
        self.refresh_button = ActionButton("刷新", "secondary")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        row.addWidget(self._status_label, 1)
        row.addWidget(self.refresh_button)
        card.body_layout.addLayout(row)
        return card

    def set_context(self, statuses: list[dict[str, object]]) -> None:
        for status in statuses:
            workflow_id = str(status.get("workflowId", ""))
            card = self._workflow_cards.get(workflow_id)
            if card is None:
                card = WorkflowCard(
                    workflow_id=workflow_id,
                    label=str(status.get("label", workflow_id)),
                    description=str(status.get("description", "")),
                    repo_url=str(status.get("repoUrl", "")),
                )
                card.action_requested.connect(
                    lambda tk, action, wid=workflow_id: self.workflow_action_requested.emit(wid, tk, action),
                )
                insert_index = self._content_layout.count() - 1
                self._content_layout.insertWidget(insert_index, card)
                self._workflow_cards[workflow_id] = card
            targets = status.get("targets", {})
            if isinstance(targets, dict):
                card.set_targets(targets)
        total = len(statuses)
        installed = sum(
            1 for s in statuses
            if any(
                t.get("installed") for t in (s.get("targets") or {}).values()
                if isinstance(t, dict)
            )
        )
        self._status_label.setText(f"共 {total} 个工作流，{installed} 个已安装")

    def set_busy(self, refresh_busy: bool, busy_targets: set[str]) -> None:
        self.refresh_button.set_busy(refresh_busy)
        for workflow_id, card in self._workflow_cards.items():
            card_targets = {
                t.removeprefix(f"{workflow_id}:")
                for t in busy_targets
                if t.startswith(f"{workflow_id}:")
            }
            card.set_busy(card_targets)
