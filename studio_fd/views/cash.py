"""Caixa: entradas, saídas e saldo do dia ou do mês."""

from datetime import date
import logging

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QComboBox, QDateEdit, QGridLayout, QGroupBox, QHBoxLayout, QLineEdit, QMessageBox, QWidget

from studio_fd.models.payment import METHODS
from studio_fd.services.cash_service import EXPENSE_CATEGORIES, INCOME_CATEGORIES, CashService
from studio_fd.services.records import CashInput
from studio_fd.utils.dates import add_months, br_date, first_of_month, long_date, month_label
from studio_fd.utils.formatting import brl
from studio_fd.widgets.controls import DateNavigator, SegmentedControl, choose
from studio_fd.widgets.data_table import DataTable
from studio_fd.widgets.forms import FormDialog, MoneyInput, form_layout
from studio_fd.widgets.metric_card import MetricCard
from studio_fd.widgets.motion import toast
from studio_fd.widgets.visuals import icon_button, label, page_header, page_layout, panel
from datetime import timedelta


class CashDialog(FormDialog):
    def __init__(self, service: CashService, kind: str, day: date, parent=None):
        income = kind == "entrada"
        super().__init__("Nova entrada" if income else "Nova saída", "Lançar", parent,
                         "Mensalidades entram sozinhas ao registrar o pagamento em Financeiro.")
        self.service, self.kind = service, kind
        self.resize(580, 560)
        group = QGroupBox("MOVIMENTAÇÃO")
        form = form_layout(group)
        self.description = QLineEdit()
        self.description.setMaxLength(150)
        self.description.setPlaceholderText("Ex.: Avaliação física" if income else "Ex.: Conta de energia")
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(INCOME_CATEGORIES if income else EXPENSE_CATEGORIES)
        self.amount = MoneyInput()
        self.day = QDateEdit(QDate(day.year, day.month, day.day))
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat("dd/MM/yyyy")
        self.method = QComboBox()
        self.method.addItems(METHODS)
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Opcional")
        form.addRow("Descrição *", self.description)
        form.addRow("Categoria", self.category)
        form.addRow("Valor *", self.amount)
        form.addRow("Data", self.day)
        form.addRow("Forma", self.method)
        form.addRow("Observação", self.notes)
        self.body.addWidget(group)
        self.body.addStretch()
        self.save_button.clicked.connect(self.save)
        self.description.setFocus()

    def save(self) -> None:
        try:
            self.service.add(CashInput(self.day.date().toPython(), self.description.text(), self.category.currentText(),
                                       self.kind, self.amount.cents(), self.method.currentText(), self.notes.text()))
        except Exception as error:
            self.show_error(error)
            return
        self.accept()


class CashView(QWidget):
    changed = Signal()

    def __init__(self, service: CashService):
        super().__init__()
        self.service = service
        layout = page_layout(self)
        income = icon_button("Entrada", "arrow-down")
        income.clicked.connect(lambda: self.add("entrada"))
        expense = icon_button("Saída", "arrow-up", "primaryButton")
        expense.clicked.connect(lambda: self.add("saida"))
        self.subtitle = label("")
        layout.addLayout(page_header("FINANCEIRO", "Caixa", self.subtitle, [income, expense]))
        self.period = SegmentedControl(["Dia", "Mês"])
        self.period.changed.connect(self.change_period)
        self.day_nav = DateNavigator("day")
        self.month_nav = DateNavigator("month")
        self.month_nav.hide()
        for navigator in (self.day_nav, self.month_nav):
            navigator.changed.connect(lambda _v: self.refresh())
        tools = QHBoxLayout()
        tools.addWidget(self.day_nav)
        tools.addWidget(self.month_nav)
        tools.addStretch()
        tools.addWidget(self.period)
        layout.addLayout(tools)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.income = MetricCard("Entradas", "R$ 0,00", "", icon_name="arrow-down")
        self.expense = MetricCard("Saídas", "R$ 0,00", "", icon_name="arrow-up")
        self.balance = MetricCard("Saldo", "R$ 0,00", "", accent=True, icon_name="wallet")
        for column, card in enumerate((self.income, self.expense, self.balance)):
            grid.addWidget(card, 0, column)
            grid.setColumnStretch(column, 1)
        layout.addLayout(grid)

        card, body = panel(margins=(0, 6, 0, 0), spacing=0)
        self.table = DataTable(["Descrição", "Categoria", "Data", "Forma", "Valor"], [3.4, 1.5, 1.1, 1.1, 1.3])
        self.table.setMinimumHeight(360)
        self.table.row_menu.connect(lambda key, _p: self.actions(key))
        self.table.cellClicked.connect(lambda row, _c: self.actions(self.table.key(row)))
        body.addWidget(self.table)
        layout.addWidget(card, 1)
        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        self.refresh()

    def change_period(self, index: int) -> None:
        self.day_nav.setVisible(index == 0)
        self.month_nav.setVisible(index == 1)
        self.refresh()

    def bounds(self) -> tuple[date, date, str]:
        if self.period.index == 0:
            day = self.day_nav.value
            return day, day, long_date(day)
        month = self.month_nav.value
        return month, add_months(month, 1) - timedelta(days=1), month_label(month)

    def refresh(self) -> None:
        start, end, text = self.bounds()
        try:
            records = self.service.entries(start, end)
        except Exception:
            logging.getLogger(__name__).exception("Falha ao carregar o caixa")
            self.feedback.setText("Não foi possível carregar o caixa.")
            return
        self.entries = {item.id: item for item in records}
        income = sum(item.amount_cents for item in records if item.kind == "entrada")
        expense = sum(item.amount_cents for item in records if item.kind == "saida")
        self.income.set_value(brl(income), f"{sum(1 for i in records if i.kind == 'entrada')} lançamento(s)")
        self.expense.set_value(brl(expense), f"{sum(1 for i in records if i.kind == 'saida')} lançamento(s)")
        balance = income - expense
        self.balance.set_value(("− " if balance < 0 else "") + brl(abs(balance)), "Entradas menos saídas")
        self.subtitle.setText(f"{text}  ·  {len(records)} movimentação(ões)")
        self.table.set_rows([(item.id, [
            (item.description, "strong"), (item.category, "muted"), (br_date(item.day), "muted"),
            (item.method or "—", "muted"),
            (("+ " if item.kind == "entrada" else "− ") + brl(item.amount_cents), "income" if item.kind == "entrada" else "expense"),
        ]) for item in records])
        self.feedback.setText("" if records else "Nenhuma movimentação neste período.")

    def add(self, kind: str) -> None:
        start, _end, _text = self.bounds()
        day = start if self.period.index == 0 else date.today()
        if CashDialog(self.service, kind, day, self).exec():
            toast(self, "Entrada lançada" if kind == "entrada" else "Saída lançada")
            self.refresh()
            self.changed.emit()

    def actions(self, entry_id) -> None:
        entry = getattr(self, "entries", {}).get(entry_id)
        if entry is None:
            return
        if choose(self, [("delete", "Excluir movimentação", "trash")]) != "delete":
            return
        if QMessageBox.question(self, "Excluir", f"Excluir “{entry.description}”?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete(entry.id)
            toast(self, "Movimentação excluída", "info")
        except ValueError as error:
            toast(self, str(error), "error")
        self.refresh()
        self.changed.emit()
