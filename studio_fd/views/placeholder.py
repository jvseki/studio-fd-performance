from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from studio_fd.views.dashboard import label


class PlaceholderView(QWidget):
    def __init__(self, title: str, description: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        layout.addWidget(label("STUDIO FD PERFORMANCE", "eyebrow"))
        layout.addWidget(label(title, "title"))
        panel = QFrame()
        panel.setObjectName("panel")
        content = QVBoxLayout(panel)
        content.setContentsMargins(26, 26, 26, 26)
        content.setSpacing(12)
        content.addWidget(label("Uma próxima etapa do seu sistema", "sectionTitle"))
        content.addWidget(label(description))
        content.addWidget(label("Esta tela ainda não realiza operações. Estamos construindo o projeto por etapas.", "caption"))
        layout.addWidget(panel)
        layout.addStretch()
