import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLineEdit, QMessageBox, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from studio_fd.services.plan_service import PlanService
from studio_fd.services.records import PlanInput, PlanRecord
from studio_fd.utils.formatting import brl
from studio_fd.views import theme
from studio_fd.views.dashboard import clear
from studio_fd.widgets.forms import FormDialog, MoneyInput, form_layout
from studio_fd.widgets.visuals import divider, icon_button, icon_label, label, page_header, page_layout, pill


class PlanDialog(FormDialog):
    def __init__(self, service: PlanService, record: PlanRecord | None = None, parent=None):
        super().__init__("Editar plano" if record else "Novo plano", "Salvar plano", parent,
                         "Os donos definem os próprios planos; nada fica fixo no sistema.")
        self.service = service
        self.record = record
        self.saved_record = None
        group = QGroupBox("DADOS DO PLANO")
        form = form_layout(group)
        self.name = QLineEdit(record.name if record else "")
        self.name.setMaxLength(100)
        self.name.setPlaceholderText("Ex.: Treino 3 vezes por semana")
        self.workouts = QSpinBox()
        self.workouts.setRange(1, 7)
        self.workouts.setValue(record.workouts_per_week if record else 1)
        self.workouts.setSuffix(" por semana")
        self.price = MoneyInput()
        if record:
            self.price.set_cents(record.price_cents)
        self.duration = QSpinBox()
        self.duration.setRange(1, 120)
        self.duration.setSuffix(" mês(es)")
        self.duration.setValue(record.duration_months if record else 1)
        self.active = QCheckBox("Plano ativo para novas matrículas")
        self.active.setChecked(record.active if record else True)
        self.description = QTextEdit()
        self.description.setAcceptRichText(False)
        self.description.setPlaceholderText("Opcional")
        self.description.setMaximumHeight(100)
        self.description.setPlainText(record.description or "" if record else "")
        form.addRow("Nome *", self.name)
        form.addRow("Treinos", self.workouts)
        form.addRow("Mensalidade", self.price)
        form.addRow("Duração", self.duration)
        form.addRow("", self.active)
        form.addRow("Descrição", self.description)
        self.body.addWidget(group)
        self.body.addWidget(label("Alterar o preço deste plano não modifica a mensalidade já combinada com cada aluno.", "caption"))
        self.body.addStretch()
        self.save_button.clicked.connect(self.save)
        self.name.setFocus()

    def save(self) -> None:
        try:
            data = PlanInput(self.name.text(), self.workouts.value(), self.price.cents(), self.duration.value(), self.description.toPlainText(), self.active.isChecked())
            self.saved_record = self.service.save(data, self.record.id if self.record else None)
        except Exception as error:
            self.show_error(error)
            return
        self.accept()


class ClickableCard(QFrame):
    clicked = Signal()

    def __init__(self, role: str):
        super().__init__()
        self.setObjectName(role)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)


def duration_text(months: int) -> str:
    return "/mês" if months == 1 else f"/ {months} meses"


class PlanCard(ClickableCard):
    def __init__(self, record: PlanRecord):
        super().__init__("planCard")
        self.record = record
        self.setMinimumHeight(196)
        self.setAccessibleName(f"Editar plano {record.name}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(label(record.name, "sectionTitle"), 1)
        top.addWidget(pill("Ativo" if record.active else "Inativo", "success" if record.active else "muted"), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)
        price = QHBoxLayout()
        price.setSpacing(6)
        value = label(brl(record.price_cents), "metricValue", wrap=False)
        price.addWidget(value)
        price.addWidget(label(duration_text(record.duration_months), "caption", wrap=False), 0, Qt.AlignmentFlag.AlignBottom)
        price.addStretch()
        layout.addLayout(price)
        meta = QHBoxLayout()
        meta.setSpacing(8)
        meta.addWidget(icon_label("calendar", theme.GOLD, 15))
        meta.addWidget(label(f"{record.workouts_per_week} treino(s) por semana", "muted", wrap=False), 1)
        layout.addLayout(meta)
        description = label(record.description or "Sem descrição.", "caption")
        description.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(description)
        layout.addStretch()
        layout.addWidget(divider())
        edit = QHBoxLayout()
        edit.addWidget(label("Editar plano", "caption"), 1)
        edit.addWidget(icon_label("arrow", theme.TEXT_3, 14))
        layout.addLayout(edit)


class PlansView(QWidget):
    changed = Signal()
    COLUMNS = 3

    def __init__(self, service: PlanService):
        super().__init__()
        self.service = service
        self.cards: list[PlanCard] = []
        layout = page_layout(self)
        create = icon_button("Novo plano", "plus", "primaryButton")
        create.clicked.connect(lambda: self.edit())
        layout.addLayout(page_header("CADASTROS", "Planos", label("Defina frequência, valor e duração. Clique em um plano para editar."), [create]))
        self.grid = QGridLayout()
        self.grid.setSpacing(14)
        for column in range(self.COLUMNS):
            self.grid.setColumnStretch(column, 1)
        layout.addLayout(self.grid)
        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        try:
            records = self.service.list()
        except Exception:
            logging.getLogger(__name__).exception("Falha ao consultar planos")
            self.feedback.setText("Não foi possível carregar os planos. Troque de tela e volte para tentar novamente.")
            return
        clear(self.grid)
        self.cards = []
        for index, record in enumerate(records):
            card = PlanCard(record)
            card.clicked.connect(lambda plan_id=record.id: self.edit(plan_id))
            self.cards.append(card)
            self.grid.addWidget(card, *divmod(index, self.COLUMNS))
        new = ClickableCard("newCard")
        new.setMinimumHeight(196)
        new.setAccessibleName("Criar novo plano")
        new_layout = QVBoxLayout(new)
        new_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        new_layout.setSpacing(8)
        new_layout.addWidget(icon_label("plus", theme.GOLD, 22), 0, Qt.AlignmentFlag.AlignHCenter)
        caption = label("Novo plano", "muted", wrap=False)
        new_layout.addWidget(caption, 0, Qt.AlignmentFlag.AlignHCenter)
        new.clicked.connect(lambda: self.edit())
        self.grid.addWidget(new, *divmod(len(records), self.COLUMNS))
        self.feedback.setText(f"{len(records)} plano(s)  ·  planos inativos preservam as matrículas existentes." if records else "Nenhum plano cadastrado ainda.")

    def edit(self, plan_id: int | None = None) -> None:
        try:
            record = self.service.get(plan_id) if plan_id is not None else None
        except Exception:
            QMessageBox.warning(self, "Não foi possível abrir", "Atualize a lista e tente novamente.")
            return
        if PlanDialog(self.service, record, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.changed.emit()
