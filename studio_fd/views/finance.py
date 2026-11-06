"""Mensalidades por competência: gerar, filtrar, registrar e desfazer pagamentos."""

from datetime import date
import logging

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QComboBox, QDateEdit, QGridLayout, QGroupBox, QHBoxLayout, QLineEdit, QMessageBox, QWidget

from studio_fd.models.payment import METHODS
from studio_fd.services.finance_service import FinanceService
from studio_fd.services.records import PaymentRecord
from studio_fd.services.student_service import StudentService
from studio_fd.utils.dates import br_date, day_in_month, month_label
from studio_fd.utils.formatting import brl
from studio_fd.widgets.controls import DateNavigator, SegmentedControl, StudentPicker, choose
from studio_fd.widgets.data_table import DataTable
from studio_fd.widgets.forms import FormDialog, MoneyInput, form_layout
from studio_fd.widgets.metric_card import MetricCard
from studio_fd.widgets.motion import toast
from studio_fd.widgets.visuals import icon_button, label, page_header, page_layout, panel

TONES = {"Pago": "pill:success", "Pendente": "pill:gold", "Atrasado": "pill:danger"}
FILTERS = ["Todas", "Atrasadas", "Pendentes", "Pagas"]
FILTER_STATUS = {1: "Atrasado", 2: "Pendente", 3: "Pago"}


class PaymentDialog(FormDialog):
    def __init__(self, service: FinanceService, record: PaymentRecord, parent=None):
        super().__init__("Registrar pagamento", "Confirmar recebimento", parent,
                         f"{record.student_name} · {month_label(record.reference_month)}. O valor entra no Caixa automaticamente.")
        self.service, self.record = service, record
        self.resize(560, 440)
        group = QGroupBox("RECEBIMENTO")
        form = form_layout(group)
        self.amount = MoneyInput()
        self.amount.set_cents(record.amount_cents)
        self.paid_on = QDateEdit(QDate.currentDate())
        self.paid_on.setCalendarPopup(True)
        self.paid_on.setDisplayFormat("dd/MM/yyyy")
        self.paid_on.setMaximumDate(QDate.currentDate())
        self.method = QComboBox()
        self.method.addItems(METHODS)
        form.addRow("Valor recebido", self.amount)
        form.addRow("Data", self.paid_on)
        form.addRow("Forma", self.method)
        self.body.addWidget(group)
        self.body.addStretch()
        self.save_button.clicked.connect(self.save)

    def save(self) -> None:
        try:
            self.service.register(self.record.id, self.paid_on.date().toPython(), self.method.currentText(), self.amount.cents())
        except Exception as error:
            self.show_error(error)
            return
        self.accept()


class ChargeDialog(FormDialog):
    """Mensalidade avulsa para um aluno (por exemplo, sem valor fixo na ficha)."""

    def __init__(self, service: FinanceService, students: StudentService, month: date, parent=None):
        super().__init__("Nova mensalidade", "Lançar mensalidade", parent, f"Competência {month_label(month)}.")
        self.service, self.month = service, month
        self.resize(580, 500)
        group = QGroupBox("COBRANÇA")
        form = form_layout(group)
        self.student = StudentPicker(students.list(active=True))
        self.amount = MoneyInput()
        due = day_in_month(month, 10)
        self.due = QDateEdit(QDate(due.year, due.month, due.day))
        self.due.setCalendarPopup(True)
        self.due.setDisplayFormat("dd/MM/yyyy")
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Opcional")
        form.addRow("Aluno *", self.student)
        form.addRow("Valor *", self.amount)
        form.addRow("Vencimento", self.due)
        form.addRow("Observação", self.notes)
        self.body.addWidget(group)
        self.body.addStretch()
        self.save_button.clicked.connect(self.save)

    def save(self) -> None:
        student_id = self.student.student_id()
        if student_id is None:
            self.feedback.setText("Escolha um aluno da lista.")
            return
        try:
            self.service.add(student_id, self.month, self.amount.cents(), self.due.date().toPython(), self.notes.text())
        except Exception as error:
            self.show_error(error)
            return
        self.accept()


class FinanceView(QWidget):
    changed = Signal()
    open_student = Signal(int)

    def __init__(self, service: FinanceService, students: StudentService):
        super().__init__()
        self.service, self.students = service, students
        self.records: dict[int, PaymentRecord] = {}
        layout = page_layout(self)
        generate = icon_button("Gerar mensalidades", "repeat", "primaryButton")
        generate.clicked.connect(self.generate)
        add = icon_button("Avulsa", "plus")
        add.clicked.connect(self.add)
        self.subtitle = label("")
        layout.addLayout(page_header("FINANCEIRO", "Mensalidades", self.subtitle, [add, generate]))
        self.navigator = DateNavigator("month")
        self.navigator.changed.connect(lambda _m: self.refresh())
        self.filter = SegmentedControl(FILTERS)
        self.filter.changed.connect(lambda _i: self.refresh())
        tools = QHBoxLayout()
        tools.addWidget(self.navigator)
        tools.addStretch()
        tools.addWidget(self.filter)
        layout.addLayout(tools)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.expected = MetricCard("Previsto no mês", "R$ 0,00", "", icon_name="trend")
        self.received = MetricCard("Recebido", "R$ 0,00", "", accent=True, icon_name="check")
        self.pending = MetricCard("A receber", "R$ 0,00", "", icon_name="clock")
        self.overdue = MetricCard("Em atraso", "R$ 0,00", "", icon_name="info")
        for column, card in enumerate((self.expected, self.received, self.pending, self.overdue)):
            grid.addWidget(card, 0, column)
            grid.setColumnStretch(column, 1)
        layout.addLayout(grid)

        card, body = panel(margins=(0, 6, 0, 0), spacing=0)
        self.table = DataTable(["Aluno", "Valor", "Vencimento", "Pagamento", "Forma", "Situação"], [3, 1.4, 1.3, 1.3, 1.1, 1.2])
        self.table.setMinimumHeight(380)
        self.table.cellClicked.connect(lambda row, _c: self.actions(self.table.key(row)))
        self.table.row_menu.connect(lambda key, _pos: self.actions(key))
        body.addWidget(self.table)
        layout.addWidget(card, 1)
        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        self.refresh()

    def refresh(self) -> None:
        month = self.navigator.value
        try:
            records = self.service.month(month)
            summary = self.service.summary(month)
        except Exception:
            logging.getLogger(__name__).exception("Falha ao carregar mensalidades")
            self.feedback.setText("Não foi possível carregar as mensalidades.")
            return
        self.records = {item.id: item for item in records}
        self.expected.set_value(brl(summary.expected_cents), f"{len(records)} mensalidade(s) lançada(s)")
        self.received.set_value(brl(summary.received_cents), f"{summary.paid} paga(s)")
        self.pending.set_value(brl(summary.pending_cents), f"{summary.pending} dentro do prazo")
        self.overdue.set_value(brl(summary.overdue_cents), f"{summary.overdue} vencida(s)" if summary.overdue else "Nenhum atraso")
        status = FILTER_STATUS.get(self.filter.index)
        shown = [item for item in records if status is None or item.status == status]
        self.table.set_rows([(item.id, [
            (item.student_name, "avatar"), (brl(item.amount_cents), "strong"), (br_date(item.due_date), "muted"),
            (br_date(item.paid_on), "muted"), (item.method or "—", "muted"), (item.status, TONES[item.status]),
        ]) for item in shown])
        self.subtitle.setText(f"Competência {month_label(month)}  ·  clique em uma mensalidade para registrar ou desfazer")
        hint = ""
        if summary.missing:
            hint = f"{summary.missing} aluno(s) ativo(s) com mensalidade combinada ainda sem cobrança neste mês — use Gerar mensalidades."
        elif not records:
            hint = "Nenhuma mensalidade neste mês. Gere a partir das fichas dos alunos ou lance uma avulsa."
        self.feedback.setText(hint)

    def generate(self) -> None:
        month = self.navigator.value
        try:
            count = self.service.generate(month)
        except Exception as error:
            toast(self, str(error) if isinstance(error, ValueError) else "Não foi possível gerar agora.", "error")
            return
        toast(self, f"{count} mensalidade(s) gerada(s) em {month_label(month)}" if count else "Todos já têm mensalidade neste mês", "success" if count else "info")
        self.refresh()
        self.changed.emit()

    def add(self) -> None:
        if ChargeDialog(self.service, self.students, self.navigator.value, self).exec():
            toast(self, "Mensalidade lançada")
            self.refresh()
            self.changed.emit()

    def actions(self, payment_id) -> None:
        record = self.records.get(payment_id)
        if record is None:
            return
        if record.status == "Pago":
            items = [("undo", "Desfazer pagamento", "refresh")]
        else:
            items = [("pay", "Registrar pagamento", "check")]
        items += [("profile", "Abrir ficha do aluno", "user")]
        if record.status != "Pago":
            items += [None, ("delete", "Excluir mensalidade", "trash")]
        chosen = choose(self, items)
        try:
            if chosen == "pay":
                if not PaymentDialog(self.service, record, self).exec():
                    return
                toast(self, f"Pagamento de {record.student_name} registrado")
            elif chosen == "undo":
                if QMessageBox.question(self, "Desfazer pagamento", f"Desfazer o pagamento de {record.student_name}? "
                                        "A entrada correspondente sai do Caixa.") != QMessageBox.StandardButton.Yes:
                    return
                self.service.undo(record.id)
                toast(self, "Pagamento desfeito", "info")
            elif chosen == "delete":
                self.service.delete(record.id)
                toast(self, "Mensalidade excluída", "info")
            elif chosen == "profile":
                self.open_student.emit(record.student_id)
                return
            else:
                return
        except ValueError as error:
            toast(self, str(error), "error")
        self.refresh()
        self.changed.emit()
