"""Ícones de traço desenhados para o Studio, gerados em qualquer cor.

Cada ícone é um trecho SVG numa grade 24x24. Ficam no código (e não em
arquivos) para que o executável nunca fique sem eles.
"""

from functools import lru_cache

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap

PATHS = {
    "dashboard": '<rect x="3.5" y="3.5" width="7" height="8" rx="1.6"/><rect x="13.5" y="3.5" width="7" height="5" rx="1.6"/>'
                 '<rect x="13.5" y="11.5" width="7" height="9" rx="1.6"/><rect x="3.5" y="14.5" width="7" height="6" rx="1.6"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2.2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "users": '<circle cx="9" cy="8" r="3.6"/><path d="M2.8 20c.6-3.5 3.1-5.6 6.2-5.6s5.6 2.1 6.2 5.6"/>'
             '<path d="M15.5 4.6a3.5 3.5 0 0 1 0 6.8M17.6 14.7c2 .7 3.3 2.6 3.6 5.3"/>',
    "layers": '<path d="M12 3.5 3 8l9 4.5L21 8z"/><path d="m3 12.2 9 4.5 9-4.5M3 16.3l9 4.5 9-4.5"/>',
    "wallet": '<rect x="3" y="5.5" width="18" height="14" rx="2.4"/><path d="M3 10h18M15.5 15h2.5"/>',
    "cash": '<rect x="2.5" y="6" width="19" height="12" rx="2.2"/><circle cx="12" cy="12" r="2.6"/><path d="M6 12h.01M18 12h.01"/>',
    "file": '<path d="M14 3.5H7.2A1.9 1.9 0 0 0 5.3 5.4v13.2c0 1 .8 1.9 1.9 1.9h9.6c1 0 1.9-.8 1.9-1.9V8z"/>'
            '<path d="M14 3.5V8h4.7M9 13h6M9 16.5h4"/>',
    "chart": '<path d="M3.5 20.5h17M7 17v-5M12 17V7M17 17v-8"/>',
    "database": '<ellipse cx="12" cy="6" rx="7.5" ry="2.8"/><path d="M4.5 6v6c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8V6"/>'
                '<path d="M4.5 12v6c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8v-6"/>',
    "sliders": '<path d="M4 6.5h9M17 6.5h3M4 12h3M11 12h9M4 17.5h11M19 17.5h1"/>'
               '<circle cx="15" cy="6.5" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="17.5" r="2"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "message": '<path d="M20.5 11.6a8.4 8.4 0 0 1-12.4 7.4L3.5 20.5 5 16a8.4 8.4 0 1 1 15.5-4.4z"/>',
    "edit": '<path d="M4 20h4.2L19 9.2a2.1 2.1 0 0 0 0-3L17.8 5a2.1 2.1 0 0 0-3 0L4 15.8z"/><path d="m13.5 6.5 4 4"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20 4.5v4.8h-4.8"/>',
    "phone": '<path d="M6.6 3.5h2.6l1.4 4.1-2 1.4a12 12 0 0 0 6.4 6.4l1.4-2 4.1 1.4v2.6a2 2 0 0 1-2.2 2A16.9 16.9 0 0 1 4.6 5.7a2 2 0 0 1 2-2.2z"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "trend": '<path d="m3.5 16.5 5.5-5.5 4 4 7.5-7.5"/><path d="M15 7.5h5.5V13"/>',
    "tag": '<path d="M3.5 12.3V4.5a1 1 0 0 1 1-1h7.8l8.2 8.2a1.4 1.4 0 0 1 0 2l-6.8 6.8a1.4 1.4 0 0 1-2 0z"/><circle cx="8" cy="8" r="1.3"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8h.01"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "lock": '<rect x="4.5" y="10.5" width="15" height="10" rx="2.2"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
    "sparkle": '<path d="M12 3.5v4M12 16.5v4M3.5 12h4M16.5 12h4M6 6l2.6 2.6M15.4 15.4 18 18M18 6l-2.6 2.6M8.6 15.4 6 18"/>',
    "chevron-left": '<path d="m14.5 6-6 6 6 6"/>',
    "chevron-right": '<path d="m9.5 6 6 6-6 6"/>',
    "trash": '<path d="M4.5 7h15M9.5 7V4.8c0-.7.5-1.3 1.2-1.3h2.6c.7 0 1.2.6 1.2 1.3V7M6.5 7l.8 12.2c.1 1 .9 1.8 1.9 1.8h5.6c1 0 1.8-.8 1.9-1.8L17.5 7"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4.5 20.5c.8-4 3.8-6.3 7.5-6.3s6.7 2.3 7.5 6.3"/>',
    "download": '<path d="M12 4v11M7 10.5l5 5 5-5M4.5 19.5h15"/>',
    "upload": '<path d="M12 15.5V4.5M7 9l5-5 5 5M4.5 19.5h15"/>',
    "folder": '<path d="M3.5 7.2c0-1 .8-1.7 1.7-1.7h4.2l2 2.2h7.4c1 0 1.7.8 1.7 1.7v8.4c0 1-.8 1.7-1.7 1.7H5.2c-1 0-1.7-.8-1.7-1.7z"/>',
    "repeat": '<path d="M4.5 11V9.5a3 3 0 0 1 3-3h12M16.5 3.5l3 3-3 3M19.5 13v1.5a3 3 0 0 1-3 3h-12M7.5 20.5l-3-3 3-3"/>',
    "command": '<path d="M9 6.5A2.5 2.5 0 1 0 6.5 9H9zM15 6.5A2.5 2.5 0 1 1 17.5 9H15zM9 17.5A2.5 2.5 0 1 1 6.5 15H9zM15 17.5a2.5 2.5 0 1 0 2.5-2.5H15zM9 9h6v6H9z"/>',
    "sidebar": '<rect x="3.5" y="4.5" width="17" height="15" rx="2.2"/><path d="M9.5 4.5v15"/>',
    "minus": '<path d="M5 12h14"/>',
    "arrow-down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "arrow-up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "shield": '<path d="M12 3.5 5 6.2v5.3c0 4.3 2.9 7.6 7 9 4.1-1.4 7-4.7 7-9V6.2z"/><path d="m9 12 2.2 2.2L15.5 10"/>',
    "external": '<path d="M13.5 4.5h6v6M19.5 4.5 11 13M17 13.5v4.3c0 1-.8 1.7-1.7 1.7H6.2c-1 0-1.7-.8-1.7-1.7V8.7c0-1 .8-1.7 1.7-1.7h4.3"/>',
}


@lru_cache(maxsize=256)
def pixmap(name: str, color: str, size: int = 18, stroke: float = 1.6) -> QPixmap:
    scale = 3
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size * scale}" height="{size * scale}" viewBox="0 0 24 24" '
           f'fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
           f'{PATHS[name]}</svg>')
    result = QPixmap()
    result.loadFromData(QByteArray(svg.encode()), "SVG")
    result.setDevicePixelRatio(scale)
    return result


def icon(name: str, color: str, size: int = 18) -> QIcon:
    return QIcon(pixmap(name, color, size))
