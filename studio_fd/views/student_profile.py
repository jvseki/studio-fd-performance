from datetime import date

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.dates import month_label
from studio_fd.utils.formatting import brl, display_phone
from studio_fd.views import theme
from studio_fd.services.anamnesis_service import AnamnesisRecord
from studio_fd.views.agenda import BookingDialog
from studio_fd.views.contracts import ContractDialog, open_contract
from studio_fd.views.dashboard import clear
from studio_fd.views.student_form import StudentDialog
from studio_fd.views.whatsapp import WhatsAppDialog
from studio_fd.widgets.forms import fit_dialog
from studio_fd.widgets.motion import smooth, toast
from studio_fd.widgets.visuals import Avatar, icon_button, icon_label, label, panel, pill, set_pill


def plain(text: str, role: str = "fieldValue") -> QLabel:
    widget = label(text, role)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


class StudentProfile(QDialog):
    changed = Signal()

    def __init__(self, student_id: int, service: StudentService, plans: PlanService, parent=None, extras=None):
        super().__init__(parent)
        self.student_id = student_id
        self.service = service
        self.plans = plans
        self.setWindowTitle("Ficha do aluno")
        self.resize(820, 780)
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
                  ("address", "Endereço"), ("trainer", "Personal"), ("registered", "Cadastro"), ("plan", "Plano"), ("fee", "Mensalidade"), ("due", "Vencimento")]
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

        self.extras = extras
        self.sections = {}
        if extras is not None:
            for key, title, button_text, icon_name in (("schedule", "Horários", "Agendar", "calendar"),
                                                       ("payments", "Histórico financeiro", "", "wallet"),
                                                       ("contracts", "Contrato", "Anexar contrato", "file"),
                                                       ("anamneses", "Anamneses", "Anexar PDF", "file")):
                box, box_layout = panel(margins=(22, 16, 22, 18), spacing=8)
                top = QHBoxLayout()
                top.setSpacing(10)
                top.addWidget(icon_label(icon_name, theme.GOLD, 16))
                top.addWidget(label(title, "sectionTitle"), 1)
                if button_text:
                    action = icon_button(button_text, "plus", "ghostButton")
                    action.setAutoDefault(False)
                    action.clicked.connect(lambda _=False, k=key: self.section_action(k))
                    top.addWidget(action)
                box_layout.addLayout(top)
                content_layout = QVBoxLayout()
                content_layout.setSpacing(6)
                box_layout.addLayout(content_layout)
                self.sections[key] = content_layout
                body.addWidget(box)
        body.addStretch()
        scroll.setWidget(content)
        smooth(scroll)
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
            "trainer": student.trainer_name or "Não definido",
        }
        for key, value in values.items():
            self.fields[key].setText(value)
            if key in self.stats:
                self.stats[key].setText(value)
        self.notes.setText(student.notes or "Nenhuma observação cadastrada.")
        self.whatsapp.setEnabled(bool(student.phone))
        if self.sections:
            self.refresh_sections()

    def refresh_sections(self) -> None:
        for layout in self.sections.values():
            clear(layout)
        extras = self.extras
        habitual = extras.agenda_service.habitual(self.student_id)
        upcoming = extras.agenda_service.for_student(self.student_id, date.today(), 14)
        schedule = self.sections["schedule"]
        if habitual:
            schedule.addWidget(plain("   ·   ".join(habitual), "strong"))
        if upcoming:
            schedule.addWidget(label("Próximos: " + ", ".join(f"{item.day:%d/%m} {item.start_time}" for item in upcoming[:6]), "caption"))
        if not habitual and not upcoming:
            schedule.addWidget(label("Nenhum horário marcado nas próximas semanas.", "caption"))

        payments = extras.finance_service.for_student(self.student_id)
        history = self.sections["payments"]
        for item in payments[:6]:
            row = QHBoxLayout()
            row.addWidget(plain(month_label(item.reference_month), "fieldValue"), 1)
            row.addWidget(plain(brl(item.amount_cents), "strong"))
            detail = f"{item.method} · {item.paid_on:%d/%m}" if item.paid_on else f"vence {item.due_date:%d/%m}"
            row.addWidget(plain(detail, "caption"))
            row.addWidget(pill(item.status, {"Pago": "success", "Pendente": "gold", "Atrasado": "danger"}[item.status]))
            history.addLayout(row)
        if not payments:
            history.addWidget(label("Nenhuma mensalidade lançada. Gere as mensalidades em Financeiro.", "caption"))

        contracts = extras.contract_service.for_student(self.student_id)
        box = self.sections["contracts"]
        for item in contracts[:3]:
            row = QHBoxLayout()
            kind = "Assinado presencialmente" if item.signature_type == "presencial" else "Assinado online"
            row.addWidget(plain(f"{kind} em {item.signed_on:%d/%m/%Y}", "fieldValue"), 1)
            if item.file_path:
                opener = icon_button("Abrir contrato", "external")
                opener.setAutoDefault(False)
                opener.clicked.connect(lambda _=False, r=item: open_contract(self, extras.contract_service, r))
                row.addWidget(opener)
            box.addLayout(row)
        if not contracts:
            box.addWidget(label("Nenhum contrato anexado.", "caption"))

        anamneses = extras.anamnesis_service.for_student(self.student_id)
        box = self.sections["anamneses"]
        for item in anamneses:
            row = QHBoxLayout()
            row.setSpacing(6)
            names = QVBoxLayout()
            names.setSpacing(1)
            names.addWidget(plain(f"{item.attached_on:%d/%m/%Y}  ·  {item.original_name}", "fieldValue"))
            if item.notes:
                names.addWidget(plain(item.notes, "caption"))
            row.addLayout(names, 1)
            for text, icon_name, handler in (("Abrir", "external", self.open_anamnesis), ("Salvar cópia", "download", self.save_anamnesis),
                                             ("Remover", "trash", self.remove_anamnesis)):
                button = icon_button(text, icon_name, "ghostButton")
                button.setAutoDefault(False)
                button.clicked.connect(lambda _=False, r=item, h=handler: h(r))
                row.addWidget(button)
            box.addLayout(row)
        if not anamneses:
            box.addWidget(label("Nenhuma anamnese anexada. Use Anexar PDF para guardar a anamnese preenchida.", "caption"))

    # Anamneses -------------------------------------------------------------
    def attach_anamnesis(self) -> bool:
        path, _ = QFileDialog.getOpenFileName(self, "Escolher anamnese em PDF", str(Path.home()), "PDF (*.pdf)")
        if not path:
            return False
        note, accepted = QInputDialog.getText(self, "Observação", "Observação (opcional), por exemplo \"Avaliação inicial\":")
        if not accepted:
            return False
        try:
            self.extras.anamnesis_service.add(self.student_id, Path(path), notes=note)
        except ValueError as error:
            QMessageBox.warning(self, "Anamnese não anexada", str(error))
            return False
        except Exception:
            QMessageBox.warning(self, "Anamnese não anexada", "Não foi possível anexar o PDF agora. Nada foi alterado na ficha.")
            return False
        return True

    def open_anamnesis(self, record: AnamnesisRecord) -> None:
        try:
            target = self.extras.anamnesis_service.file(record)
        except ValueError as error:
            QMessageBox.warning(self, "Não foi possível abrir", str(error))
            return
        if not target.exists():
            QMessageBox.warning(self, "Arquivo não encontrado",
                                "O PDF desta anamnese não está na pasta do Studio. Restaure um backup para recuperá-lo.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(target))):
            QMessageBox.warning(self, "Não foi possível abrir", "Instale um leitor de PDF para abrir a anamnese.")

    def save_anamnesis(self, record: AnamnesisRecord) -> None:
        destination, _ = QFileDialog.getSaveFileName(self, "Salvar cópia da anamnese", str(Path.home() / record.original_name), "PDF (*.pdf)")
        if not destination:
            return
        try:
            self.extras.anamnesis_service.save_copy(record, Path(destination))
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Cópia não salva", str(error) if isinstance(error, ValueError) else "Confira a pasta escolhida e tente de novo.")

    def remove_anamnesis(self, record: AnamnesisRecord) -> None:
        answer = QMessageBox.question(self, "Remover anamnese",
                                      f"Remover a anamnese de {record.attached_on:%d/%m/%Y} ({record.original_name})?\n"
                                      "O PDF sai da ficha e vai para a pasta anamneses/_removidos.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.extras.anamnesis_service.delete(record.id)
        self.refresh_sections()

    def section_action(self, key: str) -> None:
        extras = self.extras
        if key == "schedule":
            dialog = BookingDialog(extras.agenda_service, self.service, date.today(), parent=self, student_id=self.student_id)
            if dialog.exec():
                toast(self, f"{len(dialog.result.created)} horário(s) agendado(s)")
        elif key == "contracts":
            if not ContractDialog(extras.contract_service, self.service, self.student_id, self).exec():
                return
            toast(self, "Contrato salvo")
        elif key == "anamneses":
            if not self.attach_anamnesis():
                return
        self.refresh_sections()
        self.changed.emit()

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
