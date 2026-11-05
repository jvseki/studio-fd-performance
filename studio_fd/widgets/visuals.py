"""Peças visuais pequenas e reutilizáveis: avatar, etiqueta, cabeçalho de página."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from studio_fd.views import theme
from studio_fd.widgets.icons import icon, pixmap


def label(text: str, role: str = "muted", wrap: bool = True) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(role)
    widget.setWordWrap(wrap)
    return widget


def initials(name: str) -> str:
    parts = [part for part in (name or "").split() if part[:1].isalpha()]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def paint_avatar(painter: QPainter, rect: QRectF, name: str) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(theme.GOLD_LINE), 1))
    painter.setBrush(QColor(theme.GOLD_TINT))
    painter.drawEllipse(rect.adjusted(.5, .5, -.5, -.5))
    font = QFont("Segoe UI")
    font.setPixelSize(max(9, int(rect.height() * .36)))
    font.setWeight(QFont.Weight.DemiBold)
    painter.setFont(font)
    painter.setPen(QColor(theme.GOLD))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, initials(name))
    painter.restore()


class Avatar(QWidget):
    def __init__(self, name: str = "", size: int = 36):
        super().__init__()
        self.name = name
        self.setFixedSize(size, size)

    def set_name(self, name: str) -> None:
        self.name = name
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        paint_avatar(painter, QRectF(self.rect()), self.name)


def pill(text: str, tone: str = "muted") -> QLabel:
    widget = QLabel(text)
    widget.setObjectName("pill")
    widget.setProperty("tone", tone)
    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    widget.setSizePolicy(widget.sizePolicy().horizontalPolicy(), widget.sizePolicy().verticalPolicy())
    return widget


def set_pill(widget: QLabel, text: str, tone: str) -> None:
    widget.setText(text)
    widget.setProperty("tone", tone)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def icon_label(name: str, color: str = theme.TEXT_3, size: int = 16) -> QLabel:
    widget = QLabel()
    widget.setPixmap(pixmap(name, color, size))
    widget.setFixedSize(size, size)
    return widget


def icon_button(text: str, icon_name: str, role: str = "", color: str | None = None) -> QPushButton:
    button = QPushButton(text)
    if role:
        button.setObjectName(role)
    tint = color or (theme.GOLD_INK if role == "primaryButton" else theme.TEXT_2)
    button.setIcon(icon(icon_name, tint, 16))
    button.setIconSize(QSize(15, 15))
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    return line


def panel(role: str = "panel", margins=(20, 18, 20, 18), spacing: int = 14) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(role)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout


def page_header(eyebrow: str, title: str, subtitle: QLabel | None = None, actions: list[QWidget] = ()) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)
    titles = QVBoxLayout()
    titles.setSpacing(4)
    if eyebrow:
        titles.addWidget(label(eyebrow, "eyebrow"))
    titles.addWidget(label(title, "title"))
    if subtitle is not None:
        titles.addWidget(subtitle)
    row.addLayout(titles, 1)
    for widget in actions:
        row.addWidget(widget, 0, Qt.AlignmentFlag.AlignBottom)
    return row


def page_layout(widget: QWidget) -> QVBoxLayout:
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(36, 32, 36, 28)
    layout.setSpacing(22)
    return layout
