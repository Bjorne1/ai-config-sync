from pathlib import Path

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget

from .theme import STATE_COLORS, SURFACE, tint

LOGO_ACTIVE_ROLE = Qt.ItemDataRole.UserRole
LOGO_STATE_ROLE = Qt.ItemDataRole.UserRole + 1
LOGO_TOOL_ROLE = Qt.ItemDataRole.UserRole + 2

LOGO_FILENAMES = {
    "claude": "Claude.png",
    "codex": "OpenAI.png",
    "gemini": "Gemini.png",
    "antigravity": "antigravity.png",
}

MATRIX_COLUMNS = (
    ("windows", "claude", "", "Windows / Claude"),
    ("windows", "codex", "", "Windows / Codex"),
    ("windows", "gemini", "", "Windows / Gemini"),
    ("windows", "antigravity", "", "Windows / Antigravity"),
    ("wsl", "claude", "", "WSL / Claude"),
    ("wsl", "codex", "", "WSL / Codex"),
    ("wsl", "gemini", "", "WSL / Gemini"),
    ("wsl", "antigravity", "", "WSL / Antigravity"),
)
MATRIX_START_COLUMN = 3
MATRIX_END_COLUMN = MATRIX_START_COLUMN + len(MATRIX_COLUMNS) - 1
ACTION_COLUMN = MATRIX_END_COLUMN + 1

TABLE_HEADERS = ("选中", "名称", "类型", *(column[2] for column in MATRIX_COLUMNS), "操作")
MATRIX_GROUPS = (
    ("WIN", tuple(range(MATRIX_START_COLUMN, MATRIX_START_COLUMN + 4))),
    ("WSL", tuple(range(MATRIX_START_COLUMN + 4, MATRIX_START_COLUMN + 8))),
)

BADGE_SIZE = QSize(40, 24)
ICON_SIZE = 15
INACTIVE_BG = "#edf1f5"
INACTIVE_BORDER = "#d3dce6"


def logo_root() -> Path:
    return Path(__file__).resolve().parents[2] / "logo"


def is_matrix_cell(index: QModelIndex) -> bool:
    return MATRIX_START_COLUMN <= index.column() <= MATRIX_END_COLUMN


def is_action_cell(index: QModelIndex) -> bool:
    return index.column() == ACTION_COLUMN


def matrix_column(environment_id: str, tool_id: str) -> int:
    for offset, (env_id, current_tool_id, _label, _tooltip) in enumerate(MATRIX_COLUMNS, start=MATRIX_START_COLUMN):
        if env_id == environment_id and current_tool_id == tool_id:
            return offset
    raise ValueError(f"unknown matrix cell: {environment_id}/{tool_id}")


def find_matrix_entry(
    row: dict[str, object],
    environment_id: str,
    tool_id: str,
) -> dict[str, object] | None:
    for entry in row.get("entries", []):
        if entry["environmentId"] == environment_id and entry["toolId"] == tool_id:
            return entry
    return None


def matrix_tooltip(
    environment_id: str,
    tool_id: str,
    active: bool,
    entry: dict[str, object] | None,
) -> str:
    prefix = "Windows" if environment_id == "windows" else "WSL"
    if entry:
        return f"{prefix} / {tool_id} · {entry.get('message') or entry['state']}"
    if active:
        return f"{prefix} / {tool_id} · 已检测到目标"
    return f"{prefix} / {tool_id} · 未同步"


class ToolLogoDelegate(QStyledItemDelegate):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmaps = self._load_pixmaps()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        base = super().sizeHint(option, index)
        return QSize(max(base.width(), BADGE_SIZE.width() + 12), max(base.height(), BADGE_SIZE.height() + 10))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        if not is_matrix_cell(index):
            super().paint(painter, option, index)
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_badge(painter, option, index)
        painter.restore()

    def _paint_badge(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        tool_id = str(index.data(LOGO_TOOL_ROLE) or "")
        if not tool_id:
            return
        active = bool(index.data(LOGO_ACTIVE_ROLE))
        state = str(index.data(LOGO_STATE_ROLE) or "idle")
        border, background = self._badge_colors(state, active)
        badge_rect = self._badge_rect(option)
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(badge_rect, 8, 8)
        self._draw_logo(painter, badge_rect, tool_id, active)
        if not active:
            overlay = QColor("#c5ced8")
            overlay.setAlpha(108)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(overlay)
            painter.drawRoundedRect(badge_rect, 8, 8)

    def _badge_rect(self, option: QStyleOptionViewItem):
        left = option.rect.x() + (option.rect.width() - BADGE_SIZE.width()) // 2
        top = option.rect.y() + (option.rect.height() - BADGE_SIZE.height()) // 2
        return QRect(left, top, BADGE_SIZE.width(), BADGE_SIZE.height())

    def _draw_logo(self, painter: QPainter, badge_rect, tool_id: str, active: bool) -> None:
        pixmap = self._pixmaps.get(tool_id)
        if pixmap is None:
            return
        icon = pixmap.scaled(ICON_SIZE, ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        if not active:
            painter.setOpacity(0.42)
        left = badge_rect.x() + (badge_rect.width() - icon.width()) // 2
        top = badge_rect.y() + (badge_rect.height() - icon.height()) // 2
        painter.drawPixmap(left, top, icon)
        painter.setOpacity(1.0)

    def _badge_colors(self, state: str, active: bool) -> tuple[str, str]:
        if not active:
            return INACTIVE_BORDER, INACTIVE_BG
        foreground, _background = STATE_COLORS.get(state, STATE_COLORS["healthy"])
        return tint(foreground, 96), SURFACE

    def _load_pixmaps(self) -> dict[str, QPixmap]:
        root = logo_root()
        pixmaps: dict[str, QPixmap] = {}
        for tool_id, filename in LOGO_FILENAMES.items():
            path = root / filename
            if not path.exists():
                continue
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmaps[tool_id] = pixmap
        return pixmaps
