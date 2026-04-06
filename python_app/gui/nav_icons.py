"""Navigation bar SVG icons."""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap

_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" '
    'viewBox="0 0 16 16" fill="none" stroke="{color}" '
    'stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">'
    "{body}</svg>"
)

_ICON_BODIES: dict[str, str] = {
    "overview": (
        '<rect x="1.5" y="1.5" width="5" height="5" rx="1"/>'
        '<rect x="9.5" y="1.5" width="5" height="5" rx="1"/>'
        '<rect x="1.5" y="9.5" width="5" height="5" rx="1"/>'
        '<rect x="9.5" y="9.5" width="5" height="5" rx="1"/>'
    ),
    "skills": '<path d="M9 1.5L4 8.5h4l-1 6 5-7H8.5z"/>',
    "commands": (
        '<polyline points="3,4.5 7,8 3,11.5"/>'
        '<line x1="9" y1="12" x2="13" y2="12"/>'
    ),
    "globalRules": (
        '<path d="M8 1.5L2.5 4v3.5c0 3.5 2.5 5.5 5.5 7 3-1.5 5.5-3.5 5.5-7V4z"/>'
    ),
    "workflows": '<polyline points="1,8 4,8 6,3 8,13 10,5 12,8 15,8"/>',
    "tools": (
        '<path d="M8 2v8"/>'
        '<polyline points="4.5,7 8,10.5 11.5,7"/>'
        '<line x1="3" y1="14" x2="13" y2="14"/>'
    ),
    "cleanup": (
        '<path d="M2.5 4h11"/>'
        '<path d="M5.5 4v8.5c0 1 .7 1.5 1.5 1.5h2c.8 0 1.5-.5 1.5-1.5V4"/>'
        '<path d="M6 4V2.5c0-.3.2-.5.5-.5h3c.3 0 .5.2.5.5V4"/>'
    ),
    "config": (
        '<circle cx="8" cy="8" r="2.5"/>'
        '<path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2'
        "M3.1 3.1l1.4 1.4M11.5 11.5l1.4 1.4"
        'M12.9 3.1l-1.4 1.4M4.5 11.5l-1.4 1.4"/>'
    ),
}

_COLOR_NORMAL = "#94a3b8"
_COLOR_ACTIVE = "#e2e8f0"


def _build_icon(name: str, color: str) -> QIcon:
    body = _ICON_BODIES.get(name, "")
    if not body:
        return QIcon()
    svg = _SVG_TEMPLATE.format(color=color, body=body)
    pm = QPixmap()
    pm.loadFromData(QByteArray(svg.encode()))
    if pm.isNull():
        return QIcon()
    pm.setDevicePixelRatio(2.0)
    return QIcon(pm)


def nav_icons(name: str) -> tuple[QIcon, QIcon]:
    """Return (normal_icon, active_icon) for the given page key."""
    return _build_icon(name, _COLOR_NORMAL), _build_icon(name, _COLOR_ACTIVE)
