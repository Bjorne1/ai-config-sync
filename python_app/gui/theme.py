from PySide6.QtGui import QColor, QFont

# --- Color Palette ---

# Backgrounds
WINDOW_BACKGROUND = "#f8fafc"
SURFACE = "#ffffff"
SURFACE_ALT = "#f1f5f9"
SURFACE_MUTED = "#e2e8f0"

# Sidebar
SIDEBAR = "#1e293b"
SIDEBAR_ALT = "#334155"

# Accent
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2563eb"
ACCENT_SOFT = "#eff6ff"

# Border
BORDER = "#e2e8f0"
BORDER_FOCUS = "#3b82f6"

# Status
SUCCESS = "#16a34a"
WARNING = "#d97706"
ERROR = "#dc2626"
INFO = "#3b82f6"

# Text
TEXT_PRIMARY = "#1e293b"
TEXT_SECONDARY = "#64748b"
TEXT_MUTED = "#94a3b8"

STATE_COLORS = {
    "healthy": (SUCCESS, "#dcfce7"),
    "missing": (WARNING, "#fef3c7"),
    "outdated": (WARNING, "#ffedd5"),
    "drifted": (ERROR, "#fee2e2"),
    "ahead": (ERROR, "#fee2e2"),
    "conflict": (ERROR, "#fee2e2"),
    "source_missing": (ERROR, "#fee2e2"),
    "tool_unavailable": (TEXT_MUTED, "#f1f5f9"),
    "environment_error": (ERROR, "#fee2e2"),
    "profile_missing": (ERROR, "#fee2e2"),
    "partial": (INFO, "#dbeafe"),
    "idle": (TEXT_MUTED, "#f1f5f9"),
    "detected": (WARNING, "#fef3c7"),
}


def create_app_font(size: int, weight: int = QFont.Weight.Normal) -> QFont:
    font = QFont("Segoe UI", size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setWeight(weight)
    return font


def create_mono_font(size: int, weight: int = QFont.Weight.Medium) -> QFont:
    font = QFont("Cascadia Code", size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setWeight(weight)
    return font


def tint(color: str, alpha: int) -> str:
    qcolor = QColor(color)
    qcolor.setAlpha(alpha)
    return qcolor.name(QColor.NameFormat.HexArgb)


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        color: {TEXT_PRIMARY};
        font-family: 'Segoe UI', 'Microsoft YaHei', system-ui, sans-serif;
        font-size: 13px;
    }}
    QLabel {{
        background: transparent;
    }}
    QMainWindow, QWidget#appRoot, QWidget#workspace {{
        background: {WINDOW_BACKGROUND};
    }}
    QStackedWidget#pageStack {{
        background: transparent;
        border: 0;
    }}
    QLabel#eyebrow {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.18em;
    }}
    QLabel#title {{
        color: {TEXT_PRIMARY};
        font-size: 18px;
        font-weight: 700;
    }}
    QLabel#sectionTitle {{
        color: {TEXT_PRIMARY};
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#muted {{
        color: {TEXT_SECONDARY};
    }}
    /* Sidebar */
    QFrame#sidebar {{
        background: {SIDEBAR};
        border: none;
        border-radius: 0;
    }}
    QLabel#sidebarTitle {{
        color: #f8fafc;
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#formLabel {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }}
    QPushButton#navButton {{
        background: transparent;
        border: none;
        border-left: 3px solid transparent;
        border-radius: 6px;
        color: {TEXT_MUTED};
        font-weight: 600;
        font-size: 13px;
        min-height: 38px;
        padding: 0 16px;
        text-align: left;
    }}
    QPushButton#navButton:hover {{
        background: rgba(51, 65, 85, 0.4);
        color: #e2e8f0;
    }}
    QPushButton#navButton[active="true"] {{
        background: {tint(ACCENT, 30)};
        border-left: 3px solid {ACCENT};
        color: #e2e8f0;
    }}
    /* Cards */
    QFrame#card {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    QFrame#metricCard {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    /* Buttons */
    QPushButton#primaryButton,
    QPushButton#secondaryButton,
    QPushButton#dangerButton {{
        border-radius: 6px;
        font-weight: 600;
        font-size: 13px;
        min-height: 32px;
        padding: 0 14px;
    }}
    QPushButton#primaryButton {{
        background: {ACCENT};
        border: 1px solid {ACCENT};
        color: white;
    }}
    QPushButton#primaryButton:hover {{
        background: {ACCENT_HOVER};
        border-color: {ACCENT_HOVER};
    }}
    QPushButton#primaryButton:pressed {{
        background: #1d4ed8;
        border-color: #1d4ed8;
    }}
    QPushButton#secondaryButton {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        color: {TEXT_PRIMARY};
    }}
    QPushButton#secondaryButton:hover {{
        background: {ACCENT_SOFT};
        border-color: {ACCENT};
        color: {ACCENT};
    }}
    QPushButton#secondaryButton:pressed {{
        background: #dbeafe;
        border-color: {ACCENT_HOVER};
        color: {ACCENT_HOVER};
    }}
    QPushButton#dangerButton {{
        background: {SURFACE};
        border: 1px solid {ERROR};
        color: {ERROR};
    }}
    QPushButton#dangerButton:hover {{
        background: #fef2f2;
        border-color: {ERROR};
    }}
    QPushButton#dangerButton:pressed {{
        background: #fee2e2;
        border-color: #b91c1c;
        color: #b91c1c;
    }}
    QPushButton:disabled {{
        opacity: 0.55;
    }}
    /* Inputs */
    QLineEdit, QComboBox, QPlainTextEdit, QTableWidget, QListWidget {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 6px;
        selection-background-color: {ACCENT};
        selection-color: white;
    }}
    QLineEdit, QComboBox, QPlainTextEdit {{
        padding: 6px 10px;
    }}
    QLineEdit, QComboBox {{
        min-height: 20px;
    }}
    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QListWidget:focus {{
        border: 1.5px solid {ACCENT};
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-bottom: 1px solid {SURFACE_ALT};
    }}
    QListWidget::item:selected {{
        background: {ACCENT_SOFT};
        color: {TEXT_PRIMARY};
    }}
    /* Tables */
    QTableWidget {{
        gridline-color: {SURFACE_ALT};
        alternate-background-color: {WINDOW_BACKGROUND};
        border-radius: 6px;
        padding: 0;
    }}
    QHeaderView::section {{
        background: {WINDOW_BACKGROUND};
        border: 0;
        border-bottom: 1px solid {BORDER};
        color: {TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 600;
        padding: 8px;
    }}
    QScrollArea {{
        border: 0;
        background: transparent;
    }}
    /* Checkbox */
    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {BORDER};
        background: {SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border-color: {ACCENT};
    }}
    QTabWidget::pane {{
        border: 0;
    }}
    /* Scrollbar */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(148, 163, 184, 0.35);
        border-radius: 3px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(148, 163, 184, 0.6);
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: rgba(148, 163, 184, 0.35);
        border-radius: 3px;
        min-width: 28px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: rgba(148, 163, 184, 0.6);
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0; width: 0;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}
    """
