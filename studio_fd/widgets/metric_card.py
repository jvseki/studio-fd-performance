from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from studio_fd.views import theme
from studio_fd.widgets.visuals import icon_label


class MetricCard(QFrame):
    """Indicador do Dashboard: rótulo com ícone, número e uma linha de contexto."""

    def __init__(self, title: str, value: str, detail: str, accent: bool = False, icon_name: str = "dashboard"):
        super().__init__()
        self.setObjectName("metricCard")
        self.setMinimumHeight(128)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("metricLabel")
        top.addWidget(heading, 1)
        top.addWidget(icon_label(icon_name, theme.GOLD if accent else theme.TEXT_3, 16))
        layout.addLayout(top)
        layout.addStretch()
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricAccent" if accent else "metricValue")
        self.detail_label = QLabel(detail)
        self.detail_label.setObjectName("caption")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)

    def set_value(self, value: str, detail: str | None = None) -> None:
        self.value_label.setText(value)
        if detail is not None:
            self.detail_label.setText(detail)
