from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QFrame,
    QWidget,
)

_MARGIN_H = 16
_MARGIN_TOP = 12
_ANIM_DURATION = 280

# ---------- Level visual tokens ----------
# Each level uses a tinted translucent background, a subtle left accent bar,
# and muted foreground colours for a modern "glass-card" look.
LEVEL_CONFIG = {
    "error": {
        "icon": "\u26D4",
        "accent": "#ef4444",
        "bg": "rgba(254, 226, 226, 0.82)",
        "text": "#7f1d1d",
        "close": "#b91c1c",
        "auto_hide_ms": 0,
    },
    "warning": {
        "icon": "\u26A0\uFE0F",
        "accent": "#f59e0b",
        "bg": "rgba(254, 243, 199, 0.82)",
        "text": "#78350f",
        "close": "#92400e",
        "auto_hide_ms": 0,
    },
    "success": {
        "icon": "\u2714",
        "accent": "#10b981",
        "bg": "rgba(209, 250, 229, 0.82)",
        "text": "#064e3b",
        "close": "#047857",
        "auto_hide_ms": 5000,
    },
    "info": {
        "icon": "\u2139\uFE0F",
        "accent": "#6366f1",
        "bg": "rgba(224, 231, 255, 0.82)",
        "text": "#312e81",
        "close": "#4338ca",
        "auto_hide_ms": 8000,
    },
}


class StatusBanner(QFrame):
    """Floating frosted-glass notification banner.

    Use ``StatusBanner.attach(host)`` to parent it to *host* without
    inserting into the layout — the banner overlays from the top and
    slides in/out with a short animation.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._level = "info"
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._slide_out)
        self._slide_anim: QPropertyAnimation | None = None
        self._build_ui()
        self._apply_shadow()

    @classmethod
    def attach(cls, host: QWidget) -> "StatusBanner":
        banner = cls(host)
        host.installEventFilter(banner)
        return banner

    # --- UI -----------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 12, 10)
        layout.setSpacing(10)
        self._icon_label = QLabel("")
        self._icon_label.setFixedWidth(22)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label = QLabel("")
        self._title_label.setWordWrap(True)
        self._close_button = QPushButton("\u2715")
        self._close_button.setFixedSize(24, 24)
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_button.clicked.connect(self._slide_out)
        layout.addWidget(self._icon_label)
        layout.addWidget(self._title_label, 1)
        layout.addWidget(self._close_button)
        self.hide()

    def _apply_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

    # --- Custom paint: rounded rect + left accent bar -----------------

    def paintEvent(self, event) -> None:  # noqa: N802
        cfg = LEVEL_CONFIG.get(self._level, LEVEL_CONFIG["info"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = 10.0
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)
        # background fill
        bg = QColor(cfg["accent"])
        bg.setAlpha(18)
        painter.fillPath(path, bg)
        # semi-opaque overlay for frosted look
        overlay = QColor(255, 255, 255, 195)
        painter.fillPath(path, overlay)
        # subtle border
        border_color = QColor(cfg["accent"])
        border_color.setAlpha(50)
        painter.setPen(QPen(border_color, 1.0))
        painter.drawPath(path)
        # left accent bar
        bar_path = QPainterPath()
        bar_width = 4.0
        bar_path.addRoundedRect(rect.x(), rect.y(), bar_width, rect.height(), 2, 2)
        painter.fillPath(bar_path, QColor(cfg["accent"]))
        painter.end()

    # --- Public API ---------------------------------------------------

    def show_message(self, level: str, title: str, detail: str | None = None) -> None:
        cfg = LEVEL_CONFIG.get(level, LEVEL_CONFIG["info"])
        self._level = level
        self._auto_timer.stop()
        text = f"{title}\n{detail}" if detail else title
        self._title_label.setText(text)
        self._icon_label.setText(cfg["icon"])
        # dynamic child styles
        self.setStyleSheet(
            f"QFrame {{ background: transparent; border: none; }}"
            f"QLabel {{ color: {cfg['text']}; background: transparent;"
            f"  font-size: 13px; }}"
            f"QPushButton {{ border: none; background: transparent;"
            f"  font-size: 13px; color: {cfg['close']}; border-radius: 12px; }}"
            f"QPushButton:hover {{ background: rgba(0,0,0,0.06); }}"
        )
        self._reposition()
        self.raise_()
        self._slide_in()
        if cfg["auto_hide_ms"] > 0:
            self._auto_timer.start(cfg["auto_hide_ms"])

    def dismiss(self) -> None:
        self._auto_timer.stop()
        self._slide_out()

    # --- Slide animation ----------------------------------------------

    def _slide_in(self) -> None:
        self._stop_anim()
        self.show()
        start = QPoint(self.x(), -self.height())
        end = QPoint(self.x(), _MARGIN_TOP)
        self._animate_pos(start, end)

    def _slide_out(self) -> None:
        if not self.isVisible():
            return
        self._auto_timer.stop()
        self._stop_anim()
        start = self.pos()
        end = QPoint(self.x(), -self.height())
        anim = self._animate_pos(start, end)
        anim.finished.connect(self.hide)

    def _animate_pos(self, start: QPoint, end: QPoint) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(_ANIM_DURATION)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim = anim
        anim.start()
        return anim

    def _stop_anim(self) -> None:
        if self._slide_anim and self._slide_anim.state() == QPropertyAnimation.State.Running:
            self._slide_anim.stop()
        self._slide_anim = None

    # --- Positioning --------------------------------------------------

    def _reposition(self) -> None:
        host = self.parentWidget()
        if host is None:
            return
        width = host.width() - _MARGIN_H * 2
        if width < 100:
            width = host.width()
        self.setFixedWidth(width)
        self.adjustSize()
        if self.isVisible():
            self.move(_MARGIN_H, _MARGIN_TOP)

    def eventFilter(self, obj, event: QEvent) -> bool:  # noqa: N802
        if obj is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._reposition()
        return False


def confirm_destructive(parent, title: str, message: str) -> bool:
    answer = QMessageBox.warning(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    return answer == QMessageBox.StandardButton.Ok
