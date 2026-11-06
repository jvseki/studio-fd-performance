import logging
import string

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QHBoxLayout, QLineEdit, QMessageBox,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.formatting import brl, display_phone, search_key
from studio_fd.views import theme
from studio_fd.views.student_form import StudentDialog
from studio_fd.views.student_profile import StudentProfile
from studio_fd.widgets.data_table import DataTable
from studio_fd.widgets.icons import icon
from studio_fd.widgets.visuals import icon_button, icon_label, label, page_header, page_layout, panel


class StudentsView(QWidget):
    changed = Signal()

    def __init__(self, service: StudentService, plans: PlanService):
        super().__init__()
        self.service = service
        self.plans = plans
        self.letter = ""
        self.extras = None  # janela principal: dá acesso à agenda, financeiro e contratos na ficha
        layout = page_layout(self)
        self.subtitle = label("")
        create = icon_button("Novo aluno", "plus", "primaryButton")
        create.clicked.connect(self.create)
        layout.addLayout(page_header("CADASTROS", "Alunos", self.subtitle, [create]))

        card, body = panel(margins=(0, 0, 0, 0), spacing=0)
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(18, 16, 18, 12)
        toolbar.setSpacing(10)
        self.search = QLineEdit()
        self.search.setObjectName("searchField")
        self.search.setPlaceholderText("Pesquisar aluno pelo nome...")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Pesquisar aluno pelo nome")
        self.search.addAction(icon("search", theme.TEXT_3, 16), QLineEdit.ActionPosition.LeadingPosition)
        self.status = QComboBox()
        self.status.addItem("Todos os status", None)
        self.status.addItem("Somente ativos", True)
        self.status.addItem("Somente inativos", False)
        clear = QPushButton("Limpar")
        clear.setObjectName("ghostButton")
        clear.clicked.connect(self.clear_filters)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.status)
        toolbar.addWidget(clear)
        body.addLayout(toolbar)

        alphabet = QHBoxLayout()
        alphabet.setContentsMargins(14, 0, 14, 10)
        alphabet.setSpacing(1)
        self.letters = QButtonGroup(self)
        self.letters.setExclusive(True)
        for index, letter in enumerate(["Todos", *string.ascii_uppercase]):
            button = QPushButton(letter)
            button.setObjectName("letterButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if index == 0:
                button.setProperty("wide", True)
            self.letters.addButton(button, index)
            alphabet.addWidget(button, 0 if index == 0 else 1)
        self.letters.button(0).setChecked(True)
        self.letters.idClicked.connect(self.select_letter)
        body.addLayout(alphabet)

        self.content = QStackedWidget()
        self.table = DataTable(["Aluno", "Telefone", "Plano", "Mensalidade", "Vencimento", "Status"],
                               [3.2, 1.8, 1.9, 1.4, 1.2, 1.1])
        self.table.cellClicked.connect(self.open_row)
        self.table.itemActivated.connect(lambda item: self.open_row(item.row(), item.column()))
        self.content.addWidget(self.table)
        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(24, 48, 24, 48)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon_label("users", theme.TEXT_3, 28), 0, Qt.AlignmentFlag.AlignHCenter)
        self.empty_title = label("", "sectionTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_text = label("", "caption")
        self.empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_text)
        self.content.addWidget(empty)
        self.content.setMinimumHeight(360)
        body.addWidget(self.content, 1)
        layout.addWidget(card, 1)
        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda _text: self.search_timer.start())
        self.status.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def select_letter(self, index: int) -> None:
        self.letter = "" if index == 0 else string.ascii_uppercase[index - 1]
        self.refresh()

    def clear_filters(self) -> None:
        self.search.clear()
        self.status.setCurrentIndex(0)
        self.letters.button(0).setChecked(True)
        self.letter = ""
        self.refresh()

    def refresh(self, *_args) -> None:
        self.search_timer.stop()
        try:
            everyone = self.service.list()
            records = self.service.list(self.search.text(), self.letter, self.status.currentData())
        except Exception:
            logging.getLogger(__name__).exception("Falha ao consultar alunos")
            self.table.setRowCount(0)
            self.feedback.setText("Não foi possível carregar os alunos. Troque de tela e volte para tentar novamente.")
            return
        initials = {search_key(record.full_name)[:1].upper() for record in everyone}
        for index, letter in enumerate(string.ascii_uppercase, start=1):
            button = self.letters.button(index)
            empty = letter not in initials
            if button.property("empty") != empty:
                button.setProperty("empty", empty)
                button.style().unpolish(button)
                button.style().polish(button)
        active = sum(1 for record in everyone if record.active)
        self.subtitle.setText(f"{len(everyone)} cadastrado(s)  ·  {active} ativo(s)" if everyone else "Nenhum aluno cadastrado ainda")
        self.table.set_rows([
            (record.id, [
                (record.full_name, "avatar"),
                (display_phone(record.phone), "muted"),
                (record.plan_name or "Sem plano", "" if record.plan_name else "muted"),
                (brl(record.monthly_fee_cents) if record.monthly_fee_cents is not None else "—", ""),
                (f"Dia {record.due_day}" if record.due_day else "—", "muted"),
                ("Ativo" if record.active else "Inativo", "pill:success" if record.active else "pill:muted"),
            ]) for record in records
        ])
        filtered = bool(self.search.text().strip() or self.letter or self.status.currentData() is not None)
        if records:
            self.content.setCurrentIndex(0)
            self.feedback.setText(f"{len(records)} aluno(s) na lista  ·  clique para abrir a ficha" )
        else:
            self.content.setCurrentIndex(1)
            self.empty_title.setText("Nenhum aluno encontrado" if filtered else "Seu primeiro aluno começa aqui")
            self.empty_text.setText("Ajuste a pesquisa ou clique em Limpar." if filtered else "Clique em Novo aluno para cadastrar nome, telefone e plano.")
            self.feedback.setText("")

    def create(self) -> None:
        try:
            dialog = StudentDialog(self.service, self.plans, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.clear_filters()
                self.changed.emit()
                self.open_profile(dialog.saved_record.id)
        except Exception:
            logging.getLogger(__name__).exception("Falha ao abrir cadastro de aluno")
            QMessageBox.warning(self, "Não foi possível abrir", "Atualize a lista e tente novamente.")

    def open_row(self, row: int, _column: int) -> None:
        item = self.table.item(row, 0)
        if item:
            self.open_profile(item.data(Qt.ItemDataRole.UserRole))

    def open_profile(self, student_id: int) -> None:
        try:
            profile = StudentProfile(student_id, self.service, self.plans, self, extras=self.extras)
            profile.changed.connect(self.on_changed)
            profile.exec()
        except Exception:
            logging.getLogger(__name__).exception("Falha ao abrir ficha")
            QMessageBox.warning(self, "Não foi possível abrir", "Atualize a lista e tente abrir a ficha novamente.")

    def on_changed(self) -> None:
        self.refresh()
        self.changed.emit()
