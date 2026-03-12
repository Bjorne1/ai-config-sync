from PySide6.QtGui import QColor, QFont

WINDOW_BACKGROUND = "#f4f7fb"
SURFACE = "#ffffff"
SURFACE_ALT = "#e8edf3"
SURFACE_MUTED = "#cfd8e3"
TEXT_PRIMARY = "#24313f"
TEXT_MUTED = "#5c6d7f"
SIDEBAR = "#1f2937"
SIDEBAR_ALT = "#334155"
ACCENT = "#f97316"
ACCENT_SOFT = "#ffedd5"
BORDER = "#b8c4d1"
SUCCESS = "#15803d"
WARNING = "#d97706"
ERROR = "#b91c1c"
INFO = "#2563eb"

STATE_COLORS = {
    "healthy": (SUCCESS, "#dcfce7"),
    "missing": (WARNING, "#fef3c7"),
    "outdated": (WARNING, "#ffedd5"),
    "ahead": (ERROR, "#fee2e2"),
    "conflict": (ERROR, "#fee2e2"),
    "source_missing": (ERROR, "#fee2e2"),
    "tool_unavailable": (TEXT_MUTED, "#e2e8f0"),
    "environment_error": (ERROR, "#fee2e2"),
    "partial": (INFO, "#dbeafe"),
    "idle": (TEXT_MUTED, "#e2e8f0"),
}


def create_app_font(size: int, weight: int = QFont.Weight.Normal) -> QFont:
    font = QFont("Fira Sans", size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setWeight(weight)
    return font


def create_mono_font(size: int, weight: int = QFont.Weight.Medium) -> QFont:
    font = QFont("Fira Code", size)
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
        font-family: 'Fira Sans', 'Segoe UI', sans-serif;
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
        color: {TEXT_MUTED};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.18em;
    }}
    QLabel#title {{
        color: {TEXT_PRIMARY};
        font-size: 30px;
        font-weight: 700;
    }}
    QLabel#sectionTitle {{
        color: {TEXT_PRIMARY};
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel#muted {{
        color: {TEXT_MUTED};
    }}
    QFrame#sidebar {{
        background: {SIDEBAR};
        border: 1px solid {tint(ACCENT, 30)};
        border-radius: 28px;
    }}
    QFrame#sidebarHero {{
        background: #111827;
        border: 1px solid {tint(ACCENT, 55)};
        border-radius: 20px;
    }}
    QLabel#sidebarTitle {{
        color: #f8fafc;
        font-size: 28px;
        font-weight: 800;
    }}
    QLabel#sidebarIntro {{
        color: #94a3b8;
        font-size: 12px;
    }}
    QLabel#sidebarSectionLabel {{
        color: #7c8ea5;
        font-size: 11px;
        font-weight: 700;
        padding-left: 4px;
    }}
    QLabel#formLabel {{
        color: {TEXT_MUTED};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }}
    QPushButton#navButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 16px;
        color: #e2e8f0;
        font-weight: 700;
        min-height: 44px;
        padding: 0 14px;
        text-align: left;
    }}
    QPushButton#navButton:hover {{
        background: #273449;
        border-color: {tint(ACCENT, 80)};
    }}
    QPushButton#navButton[active="true"] {{
        background: {ACCENT};
        color: white;
    }}
    QFrame#card {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 20px;
    }}
    QFrame#metricCard {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 18px;
    }}
    QPushButton#primaryButton, QPushButton#secondaryButton, QPushButton#dangerButton {{
        border-radius: 12px;
        font-weight: 700;
        min-height: 38px;
        padding: 0 16px;
    }}
    QPushButton#primaryButton {{
        background: {ACCENT};
        border: 1px solid {ACCENT};
        color: white;
    }}
    QPushButton#primaryButton:hover {{
        background: #ea580c;
    }}
    QPushButton#secondaryButton {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        color: {TEXT_PRIMARY};
    }}
    QPushButton#secondaryButton:hover {{
        border-color: {ACCENT};
        color: {ACCENT};
    }}
    QPushButton#dangerButton {{
        background: #991b1b;
        border: 1px solid #991b1b;
        color: white;
    }}
    QPushButton#dangerButton:hover {{
        background: #7f1d1d;
    }}
    QLineEdit, QComboBox, QPlainTextEdit, QTableWidget {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
        selection-background-color: {ACCENT};
        selection-color: white;
    }}
    QLineEdit, QComboBox, QPlainTextEdit {{
        padding: 8px 10px;
    }}
    QLineEdit, QComboBox {{
        min-height: 22px;
    }}
    QTableWidget {{
        gridline-color: {SURFACE_MUTED};
        alternate-background-color: {SURFACE_ALT};
        padding: 0;
    }}
    QHeaderView::section {{
        background: {SURFACE_ALT};
        border: 0;
        border-bottom: 1px solid {BORDER};
        color: {TEXT_MUTED};
        font-size: 11px;
        font-weight: 700;
        padding: 8px;
        text-transform: uppercase;
    }}
    QScrollArea {{
        border: 0;
        background: transparent;
    }}
    QScrollArea#workspaceScroll {{
        background: transparent;
    }}
    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 5px;
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
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {SURFACE_MUTED};
        border-radius: 6px;
        min-height: 30px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
        margin: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {SURFACE_MUTED};
        border-radius: 6px;
        min-width: 30px;
    }}
    """
