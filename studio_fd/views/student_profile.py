from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.formatting import brl, display_phone
from studio_fd.views import theme
from studio_fd.views.student_form import StudentDialog
from studio_fd.views.whatsapp import WhatsAppDialog
from studio_fd.widgets.forms import fit_dialog
from studio_fd.widgets.visuals import Avatar, icon_button, icon_label, label, panel, pill, set_pill


def plain(text: str, role: str = "fieldValue") -> QLabel:
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
        self.resize(780, 740)
        self.setMinimumSize(600, 460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(28, 26, 28, 18)
        header.setSpacing(16)
        self.avatar = Avatar("", 60)
        header.addWidget(self.avatar)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        self.name = plain("", "dialogTitle")
        titles.addWidget(self.name)
        meta = QHBoxLayout()
        meta.setSpacing(10)
        self.state = pill("", "success")
        meta.addWidget(self.state)
        self.status = plain("", "caption")
        meta.addWidget(self.status, 1)
        titles.addLayout(meta)
        header.addLayout(titles, 1)
        self.whatsapp = icon_button("WhatsApp", "message")
        self.whatsapp.clicked.connect(self.open_whatsapp)
        edit = icon_button("Editar", "edit", "primaryButton")
        edit.clicked.connect(self.edit)
        header.addWidget(self.whatsapp)
        header.addWidget(edit)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(28, 4, 22, 24)
        body.setSpacing(14)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.stats = {}
        for key, title, icon_name in (("plan", "Plano", "layers"), ("fee", "Mensalidade", "tag"), ("due", "Vencimento", "clock")):
            card, card_layout = panel("metricCard", (18, 14, 18, 14), 6)
            card.setMinimumHeight(0)
            top = QHBoxLayout()
            top.setSpacing(7)
            top.addWidget(icon_label(icon_name, theme.GOLD, 14))
            top.addWidget(label(title.upper(), "fieldLabel", wrap=False), 1)
            card_layout.addLayout(top)
            value = plain("", "statValue")
            self.stats[key] = value
            card_layout.addWidget(value)
            stats.addWidget(card, 1)
        body.addLayout(stats)

        details, details_layout = panel(margins=(22, 18, 22, 20), spacing=14)
        details_layout.addWidget(label("Dados do aluno", "sectionTitle"))
        fields = QGridLayout()
        fields.setHorizontalSpacing(28)
        fields.setVerticalSpacing(16)
        self.fields = {}
        titles = [("phone", "Telefone"), ("birth", "Nascimento"), ("cpf", "CPF"), ("start", "Início"),
                  ("address", "Endereço"), ("registered", "Cadastro"), ("plan", "Plano"), ("fee", "Mensalidade"), ("due", "Vencimento")]
        visible = 0
        for key, title in titles:
            value = plain("")
            self.fields[key] = value
            if key in ("plan", "fee", "due"):
                continue  # já aparecem nos destaques acima
            cell = QVBoxLayout()
            cell.setSpacing(3)
            cell.addWidget(label(title.upper(), "fieldLabel", wrap=False))
            cell.addWidget(value)
            fields.addLayout(cell, visible // 2, visible % 2)
            visible += 1
        fields.setColumnStretch(0, 1)
        fields.setColumnStretch(1, 1)
        details_layout.addLayout(fields)
        body.addWidget(details)

        notes, notes_layout = panel(margins=(22, 18, 22, 20), spacing=8)
        notes_layout.addWidget(label("Observações", "sectionTitle"))
        self.notes = plain("", "muted")
        notes_layout.addWidget(self.notes)
        body.addWidget(notes)

        upcoming, upcoming_layout = panel("softPanel", (22, 16, 22, 18), 8)
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(label("Horários, pagamentos e contrato", "sectionTitle"), 1)
        top.addWidget(pill("Próxima etapa", "gold"))
        upcoming_layout.addLayout(top)
        upcoming_layout.addWidget(label("Esses dados serão ligados a esta ficha nas próximas etapas. A mensalidade informada aqui ainda não gera cobrança.", "caption"))
        body.addWidget(upcoming)
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("dialogFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(28, 12, 28, 12)
        footer_layout.addStretch()
        close = QPushButton("Fechar ficha")
        close.setObjectName("ghostButton")
        close.clicked.connect(self.accept)
        footer_layout.addWidget(close)
        self.close_button = close
        for button in (self.whatsapp, edit, close):
            button.setAutoDefault(False)
        layout.addWidget(footer)
        self.refresh()

    def showEvent(self, event) -> None:
        fit_dialog(self)
        super().showEvent(event)
        self.close_button.setFocus()

    def refresh(self) -> None:
        student = self.service.get(self.student_id)
        self.name.setText(student.full_name)
        self.avatar.set_name(student.full_name)
        set_pill(self.state, "Ativo" if student.active else "Inativo", "success" if student.active else "muted")
        self.status.setText(f"Aluno #{student.id}  ·  desde {student.registered_on.strftime('%d/%m/%Y')}")
        date_text = lambda value: value.strftime("%d/%m/%Y") if value else "Não informado"
        cpf = student.cpf
        cpf_text = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if cpf else "Não informado"
        plan = student.plan_name or "Sem plano"
        values = {
            "phone": display_phone(student.phone), "birth": date_text(student.birth_date), "cpf": cpf_text,
            "address": student.address or "Não informado", "plan": plan,
            "fee": brl(student.monthly_fee_cents) if student.monthly_fee_cents is not None else "Não definida",
            "due": f"Dia {student.due_day}" if student.due_day else "Não definido",
            "start": date_text(student.starts_on), "registered": date_text(student.registered_on),
        }
        for key, value in values.items():
            self.fields[key].setText(value)
            if key in self.stats:
                self.stats[key].setText(value)
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
