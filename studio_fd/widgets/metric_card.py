from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class MetricCard(QFrame):
    def __init__(self, title: str, value: str, detail: str, accent: bool = False):
        super().__init__()
        self.setObjectName("metricCard")
        self.setMinimumHeight(130)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(7)
        heading = QLabel(title)
        heading.setObjectName("muted")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricAccent" if accent else "metricValue")
        note = QLabel(detail)
        note.setObjectName("caption")
        note.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(self.value_label)
        layout.addWidget(note)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
