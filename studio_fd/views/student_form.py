from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QGroupBox, QHBoxLayout, QLineEdit,
    QPushButton, QSpinBox, QTextEdit, QWidget,
)

from studio_fd.services.plan_service import PlanService
from studio_fd.services.records import StudentInput, StudentRecord
from studio_fd.services.student_service import StudentService
from studio_fd.utils.formatting import display_phone
from studio_fd.views.plans import PlanDialog
from studio_fd.widgets.forms import FormDialog, MoneyInput, OptionalDate, form_layout


class StudentDialog(FormDialog):
    def __init__(self, service: StudentService, plans: PlanService, record: StudentRecord | None = None, parent=None):
        super().__init__("Editar aluno" if record else "Novo aluno", "Salvar aluno", parent,
                         "Nome e telefone bastam para começar. O restante é opcional.")
        self.service = service
        self.plans_service = plans
        self.record = record
        self.saved_record = None
        self.resize(700, 750)
        basic = QGroupBox("ALUNO")
        form = form_layout(basic)
        self.name = QLineEdit(record.full_name if record else "")
        self.name.setPlaceholderText("Nome completo")
        self.name.setMaxLength(150)
        self.phone = QLineEdit(display_phone(record.phone) if record and record.phone else "")
        self.phone.setPlaceholderText("(18) 99999-9999")
        self.phone.setMaxLength(30)
        self.active = QCheckBox("Aluno ativo")
        self.active.setChecked(record.active if record else True)
        form.addRow("Nome *", self.name)
        form.addRow("Telefone / WhatsApp *", self.phone)
        form.addRow("", self.active)
        self.body.addWidget(basic)

        contract = QGroupBox("PLANO E MENSALIDADE")
        contract_form = form_layout(contract)
        plan_row = QWidget()
        row_layout = QHBoxLayout(plan_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        self.plan = QComboBox()
        self.plan.setMinimumContentsLength(16)
        self.plan.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        row_layout.addWidget(self.plan, 1)
        new_plan = QPushButton("+ Novo plano")
        new_plan.setAutoDefault(False)
        new_plan.clicked.connect(self.create_plan)
        row_layout.addWidget(new_plan)
        contract_form.addRow("Plano", plan_row)
        fee_row = QWidget()
        fee_layout = QHBoxLayout(fee_row)
        fee_layout.setContentsMargins(0, 0, 0, 0)
        self.fee_enabled = QCheckBox("Informar valor")
        self.fee = MoneyInput()
        fee_layout.addWidget(self.fee_enabled)
        fee_layout.addWidget(self.fee, 1)
        self.fee_enabled.setChecked(record is not None and record.monthly_fee_cents is not None)
        self.fee.setEnabled(self.fee_enabled.isChecked())
        self.fee_enabled.toggled.connect(self.fee.setEnabled)
        if record and record.monthly_fee_cents is not None:
            self.fee.set_cents(record.monthly_fee_cents)
        self.due_day = QSpinBox()
        self.due_day.setRange(0, 31)
        self.due_day.setSpecialValueText("Não definido")
        self.due_day.setValue(record.due_day or 0 if record else 0)
        self.starts = OptionalDate(record.starts_on if record else None)
        contract_form.addRow("Mensalidade combinada", fee_row)
        contract_form.addRow("Dia do vencimento", self.due_day)
        contract_form.addRow("Data de início", self.starts)
        self.body.addWidget(contract)
        self.load_plans(record.plan_id if record else None)
        self.plan.activated.connect(self.apply_plan_price)

        self.body.addSpacing(14)
        self.more_button = QPushButton("+ Mostrar dados opcionais")
        self.more_button.setObjectName("ghostButton")
        self.more_button.setCheckable(True)
        self.more_button.setAutoDefault(False)
        self.body.addWidget(self.more_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.extra = QGroupBox("MAIS INFORMAÇÕES")
        extra_form = form_layout(self.extra)
        self.birth = OptionalDate(record.birth_date if record else None, past_only=True)
        self.cpf = QLineEdit(record.cpf or "" if record else "")
        self.cpf.setPlaceholderText("000.000.000-00")
        self.cpf.setMaxLength(14)
        self.address = QLineEdit(record.address or "" if record else "")
        self.address.setMaxLength(255)
        self.notes = QTextEdit()
        self.notes.setAcceptRichText(False)
        self.notes.setPlaceholderText("Informações importantes para o atendimento")
        self.notes.setMaximumHeight(110)
        self.notes.setPlainText(record.notes or "" if record else "")
        extra_form.addRow("Nascimento", self.birth)
        extra_form.addRow("CPF", self.cpf)
        extra_form.addRow("Endereço", self.address)
        extra_form.addRow("Observações", self.notes)
        self.body.addWidget(self.extra)
        self.extra.hide()
        self.more_button.toggled.connect(self.toggle_extra)
        self.body.addStretch()
        self.save_button.clicked.connect(self.save)
        self.name.setFocus()

    def toggle_extra(self, visible: bool) -> None:
        self.extra.setVisible(visible)
        self.more_button.setText("− Recolher dados opcionais" if visible else "+ Mostrar dados opcionais")

    def load_plans(self, selected_id: int | None) -> None:
        self.available_plans = {plan.id: plan for plan in self.plans_service.list()}
        self.plan.clear()
        self.plan.addItem("Sem plano por enquanto", None)
        for plan in self.available_plans.values():
            if plan.active or plan.id == selected_id:
                self.plan.addItem(plan.name + (" · Inativo" if not plan.active else ""), plan.id)
        index = self.plan.findData(selected_id)
        self.plan.setCurrentIndex(max(0, index))

    def apply_plan_price(self, _index: int = 0) -> None:
        plan = self.available_plans.get(self.plan.currentData())
        if plan:
            self.fee_enabled.setChecked(True)
            self.fee.set_cents(plan.price_cents)

    def create_plan(self) -> None:
        dialog = PlanDialog(self.plans_service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.load_plans(dialog.saved_record.id)
                self.apply_plan_price()
            except Exception as error:
                self.show_error(error)

    def save(self) -> None:
        try:
            data = StudentInput(
                full_name=self.name.text(), phone=self.phone.text(), birth_date=self.birth.value(),
                cpf=self.cpf.text(), address=self.address.text(), active=self.active.isChecked(),
                notes=self.notes.toPlainText(), plan_id=self.plan.currentData(),
                monthly_fee_cents=self.fee.cents() if self.fee_enabled.isChecked() else None,
                starts_on=self.starts.value(), due_day=self.due_day.value() or None,
            )
            self.saved_record = self.service.save(data, self.record.id if self.record else None)
        except Exception as error:
            self.show_error(error)
            return
        self.accept()
