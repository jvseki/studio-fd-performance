from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.formatting import brl, display_phone
from studio_fd.views.dashboard import label
from studio_fd.views.student_form import StudentDialog
from studio_fd.views.whatsapp import WhatsAppDialog
from studio_fd.widgets.forms import fit_dialog


def plain(text: str, role: str = "muted") -> QLabel:
    widget = label(text, role)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


class StudentProfile(QDialog):
    changed = Signal()

    def __init__(self, student_id: int, service: StudentService, plans: PlanService, parent=None):
        super().__init__(parent)
        self.student_id = student_id
        self.service = service
        self.plans = plans
        self.setWindowTitle("Ficha do aluno")
        self.resize(760, 760)
        self.setMinimumSize(580, 450)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        self.name = plain("", "title")
        self.status = plain("")
        layout.addWidget(self.name)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        edit = QPushButton("Editar aluno")
        edit.setObjectName("primaryButton")
        edit.clicked.connect(self.edit)
        self.whatsapp = QPushButton("WhatsApp")
        self.whatsapp.clicked.connect(self.open_whatsapp)
        actions.addWidget(edit)
        actions.addWidget(self.whatsapp)
        actions.addStretch()
        layout.addLayout(actions)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 12, 12, 12)
        body.setSpacing(18)
        panel = QFrame()
        panel.setObjectName("panel")
        fields = QGridLayout(panel)
        fields.setContentsMargins(18, 18, 18, 18)
        fields.setSpacing(12)
        self.fields = {}
        titles = [("phone", "Telefone"), ("birth", "Nascimento"), ("cpf", "CPF"), ("address", "Endereço"),
                  ("plan", "Plano"), ("fee", "Mensalidade"), ("due", "Vencimento"), ("start", "Início"), ("registered", "Cadastro")]
        for row, (key, title) in enumerate(titles):
            fields.addWidget(label(title, "caption"), row, 0)
            value = plain("")
            self.fields[key] = value
            fields.addWidget(value, row, 1)
        fields.setColumnStretch(1, 1)
        body.addWidget(panel)
        body.addWidget(label("Observações", "sectionTitle"))
        self.notes = plain("")
        body.addWidget(self.notes)
        body.addWidget(label("Treinos, pagamentos e contrato", "sectionTitle"))
        body.addWidget(label("Os horários de treino, o histórico de pagamentos e os PDFs serão vinculados nas próximas etapas. A mensalidade cadastrada aqui ainda não gera uma cobrança.", "caption"))
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        close = QPushButton("Fechar ficha")
        close.clicked.connect(self.accept)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.refresh()

    def showEvent(self, event) -> None:
        fit_dialog(self)
        super().showEvent(event)

    def refresh(self) -> None:
        student = self.service.get(self.student_id)
        self.name.setText(student.full_name)
        self.status.setText(f"{'Ativo' if student.active else 'Inativo'}  ·  Aluno #{student.id}")
        date_text = lambda value: value.strftime("%d/%m/%Y") if value else "Não informado"
        cpf = student.cpf
        cpf_text = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if cpf else "Não informado"
        values = {
            "phone": display_phone(student.phone), "birth": date_text(student.birth_date), "cpf": cpf_text,
            "address": student.address or "Não informado", "plan": student.plan_name or "Sem plano por enquanto",
            "fee": brl(student.monthly_fee_cents), "due": f"Dia {student.due_day}" if student.due_day else "Não definido",
            "start": date_text(student.starts_on), "registered": date_text(student.registered_on),
        }
        for key, value in values.items():
            self.fields[key].setText(value)
        self.notes.setText(student.notes or "Nenhuma observação cadastrada.")
        self.whatsapp.setEnabled(bool(student.phone))

    def edit(self) -> None:
        try:
            record = self.service.get(self.student_id)
            if StudentDialog(self.service, self.plans, record, self).exec() == QDialog.DialogCode.Accepted:
                self.refresh()
                self.changed.emit()
        except Exception:
            QMessageBox.warning(self, "Não foi possível abrir", "Feche a ficha, atualize a lista e tente novamente.")

    def open_whatsapp(self) -> None:
        try:
            WhatsAppDialog(self.service.get(self.student_id), self).exec()
        except Exception:
            QMessageBox.warning(self, "Não foi possível abrir", "Confira o telefone cadastrado e tente novamente.")
