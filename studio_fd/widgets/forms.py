"""Campos e estrutura compartilhados pelos formulários de cadastro."""

from datetime import date
from decimal import Decimal
import logging

from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtWidgets import (
    QCheckBox, QDateEdit, QDialog, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)


class MoneyInput(QDoubleSpinBox):
    def __init__(self):
        super().__init__()
        self.setLocale(QLocale("pt_BR"))
        self.setPrefix("R$ ")
        self.setDecimals(2)
        self.setRange(0, 9_999_999.99)
        self.setGroupSeparatorShown(True)

    def cents(self) -> int:
        return int(Decimal(str(self.value())) * 100)

    def set_cents(self, cents: int) -> None:
        self.setValue(cents / 100)


class OptionalDate(QWidget):
    def __init__(self, value: date | None = None, past_only: bool = False):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.enabled = QCheckBox("Informar")
        self.editor = QDateEdit()
        self.editor.setDisplayFormat("dd/MM/yyyy")
        self.editor.setCalendarPopup(True)
        self.editor.setMinimumDate(QDate(1900, 1, 1))
        if past_only:
            self.editor.setMaximumDate(QDate.currentDate())
        self.editor.setDate(QDate(value.year, value.month, value.day) if value else QDate.currentDate())
        self.enabled.setChecked(value is not None)
        self.editor.setEnabled(value is not None)
        self.enabled.toggled.connect(self.editor.setEnabled)
        layout.addWidget(self.enabled)
        layout.addWidget(self.editor, 1)

    def value(self) -> date | None:
        return self.editor.date().toPython() if self.enabled.isChecked() else None


def form_layout(widget: QWidget) -> QFormLayout:
    form = QFormLayout(widget)
    form.setHorizontalSpacing(18)
    form.setVerticalSpacing(12)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return form


def fit_dialog(dialog: QDialog) -> None:
    screen = dialog.screen()
    if screen is not None:
        available = screen.availableGeometry()
        dialog.resize(min(dialog.width(), max(dialog.minimumWidth(), available.width() - 40)),
                      min(dialog.height(), max(dialog.minimumHeight(), available.height() - 60)))


class FormDialog(QDialog):
    def __init__(self, title: str, save_text: str, parent=None, subtitle: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(660, 640)
        self.setMinimumSize(560, 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QVBoxLayout()
        header.setContentsMargins(28, 24, 28, 4)
        header.setSpacing(4)
        heading = QLabel(title)
        heading.setObjectName("dialogTitle")
        header.addWidget(heading)
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("caption")
        self.subtitle.setWordWrap(True)
        self.subtitle.setVisible(bool(subtitle))
        header.addWidget(self.subtitle)
        layout.addLayout(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(28, 4, 22, 20)
        self.body.setSpacing(4)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        footer = QFrame()
        footer.setObjectName("dialogFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(28, 14, 28, 14)
        footer_layout.setSpacing(10)
        self.feedback = QLabel()
        self.feedback.setObjectName("formError")
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        footer_layout.addWidget(self.feedback, 1)
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("ghostButton")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton(save_text)
        self.save_button.setObjectName("primaryButton")
        self.save_button.setDefault(True)
        footer_layout.addWidget(cancel)
        footer_layout.addWidget(self.save_button)
        layout.addWidget(footer)

    def showEvent(self, event) -> None:
        fit_dialog(self)
        super().showEvent(event)

    def show_error(self, error: Exception) -> None:
        if isinstance(error, ValueError):
            self.feedback.setText(str(error))
        else:
            logging.getLogger(__name__).exception("Falha na operação do formulário")
            self.feedback.setText("Não foi possível salvar agora. Tente novamente. Seus campos continuam preenchidos.")
