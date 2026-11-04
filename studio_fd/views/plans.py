import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QGroupBox, QHeaderView, QHBoxLayout,
    QLineEdit, QMessageBox, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from studio_fd.services.plan_service import PlanService
from studio_fd.services.records import PlanInput, PlanRecord
from studio_fd.utils.formatting import brl
from studio_fd.views.dashboard import label
from studio_fd.widgets.forms import FormDialog, MoneyInput, form_layout


class PlanDialog(FormDialog):
    def __init__(self, service: PlanService, record: PlanRecord | None = None, parent=None):
        super().__init__("Editar plano" if record else "Novo plano", "Salvar plano", parent)
        self.service = service
        self.record = record
        self.saved_record = None
        group = QGroupBox("Dados do plano")
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


class PlansView(QWidget):
    changed = Signal()

    def __init__(self, service: PlanService):
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(18)
        header = QHBoxLayout()
        header.addWidget(label("Planos", "title"), 1)
        create = QPushButton("+ Novo plano")
        create.setObjectName("primaryButton")
        create.clicked.connect(lambda: self.edit())
        header.addWidget(create)
        layout.addLayout(header)
        layout.addWidget(label("Defina seus valores. Clique em um plano para editar."))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["PLANO", "TREINOS", "MENSALIDADE", "DURAÇÃO", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.cellClicked.connect(self.open_row)
        self.table.itemActivated.connect(lambda item: self.open_row(item.row(), item.column()))
        layout.addWidget(self.table, 1)
        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        retry = QPushButton("Atualizar lista")
        retry.clicked.connect(self.refresh)
        layout.addWidget(retry, alignment=Qt.AlignmentFlag.AlignLeft)
        self.refresh()

    def refresh(self) -> None:
        try:
            records = self.service.list()
        except Exception:
            logging.getLogger(__name__).exception("Falha ao consultar planos")
            self.table.setRowCount(0)
            self.feedback.setText("Não foi possível carregar os planos. Clique em Atualizar lista para tentar novamente.")
            return
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = [record.name, f"{record.workouts_per_week}x por semana", brl(record.price_cents), f"{record.duration_months} mês(es)", "Ativo" if record.active else "Inativo"]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record.id)
                self.table.setItem(row, column, item)
        self.feedback.setText(f"{len(records)} plano(s). Planos inativos preservam as matrículas existentes." if records else "Nenhum plano cadastrado. Clique em + Novo plano para começar.")

    def open_row(self, row: int, _column: int) -> None:
        item = self.table.item(row, 0)
        if item:
            self.edit(item.data(Qt.ItemDataRole.UserRole))

    def edit(self, plan_id: int | None = None) -> None:
        try:
            record = self.service.get(plan_id) if plan_id is not None else None
        except Exception:
            QMessageBox.warning(self, "Não foi possível abrir", "Atualize a lista e tente novamente.")
            return
        if PlanDialog(self.service, record, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.changed.emit()
