from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from studio_fd.views import theme
from studio_fd.widgets.visuals import icon_label, label, page_header, page_layout, pill


class PlaceholderView(QWidget):
    """Tela de módulo futuro: explica o que virá, sem fingir que já funciona."""

    def __init__(self, title: str, description: str, icon_name: str = "sparkle"):
        super().__init__()
        layout = page_layout(self)
        layout.addLayout(page_header("STUDIO FD PERFORMANCE", title, label("Este módulo faz parte das próximas etapas do sistema.")))
        card = QFrame()
        card.setObjectName("softPanel")
        content = QVBoxLayout(card)
        content.setContentsMargins(48, 44, 48, 48)
        content.setSpacing(0)
        badge = QFrame()
        badge.setFixedSize(52, 52)
        badge.setStyleSheet(f"background: {theme.GOLD_TINT}; border: 1px solid {theme.GOLD_LINE}; border-radius: 14px;")
        inner = QVBoxLayout(badge)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(icon_label(icon_name, theme.GOLD, 22), 0, Qt.AlignmentFlag.AlignCenter)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(badge)
        row.addStretch()
        content.addLayout(row)
        content.addSpacing(18)
        tag = QHBoxLayout()
        tag.addStretch()
        tag.addWidget(pill("Em desenvolvimento", "gold"))
        tag.addStretch()
        content.addLayout(tag)
        content.addSpacing(14)
        heading = label(f"{title} chega em uma próxima etapa", "sectionTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content.addWidget(heading)
        content.addSpacing(8)
        text = label(description)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content.addWidget(text)
        layout.addWidget(card)
        layout.addStretch()
