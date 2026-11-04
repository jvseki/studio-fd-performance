import logging
import string

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QDialog, QGridLayout, QHeaderView,
    QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.formatting import display_phone
from studio_fd.views.dashboard import label
from studio_fd.views.student_form import StudentDialog
from studio_fd.views.student_profile import StudentProfile


class StudentsView(QWidget):
    changed = Signal()

    def __init__(self, service: StudentService, plans: PlanService):
        super().__init__()
        self.service = service
        self.plans = plans
        self.letter = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(16)
        header = QHBoxLayout()
        header.addWidget(label("Alunos", "title"), 1)
        create = QPushButton("+ Novo aluno")
        create.setObjectName("primaryButton")
        create.clicked.connect(self.create)
        header.addWidget(create)
        layout.addLayout(header)
        layout.addWidget(label("Encontre o aluno e clique no nome para abrir a ficha."))
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Pesquisar aluno...")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Pesquisar aluno pelo nome")
        self.status = QComboBox()
        self.status.addItem("Todos os status", None)
        self.status.addItem("Somente ativos", True)
        self.status.addItem("Somente inativos", False)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.status)
        clear = QPushButton("Limpar filtros")
        clear.clicked.connect(self.clear_filters)
        filters.addWidget(clear)
        layout.addLayout(filters)
        alphabet = QGridLayout()
        alphabet.setSpacing(5)
        self.letters = QButtonGroup(self)
        self.letters.setExclusive(True)
        for index, letter in enumerate(["Todos", *string.ascii_uppercase]):
            button = QPushButton(letter)
            button.setObjectName("letterButton")
            button.setCheckable(True)
            self.letters.addButton(button, index)
            alphabet.addWidget(button, index // 14, index % 14)
        self.letters.button(0).setChecked(True)
        self.letters.idClicked.connect(self.select_letter)
        layout.addLayout(alphabet)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ALUNO", "TELEFONE", "PLANO", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(50)
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
            records = self.service.list(self.search.text(), self.letter, self.status.currentData())
        except Exception:
            logging.getLogger(__name__).exception("Falha ao consultar alunos")
            self.table.setRowCount(0)
            self.feedback.setText("Não foi possível carregar os alunos. Clique em Atualizar lista para tentar novamente.")
            return
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = [record.full_name, display_phone(record.phone), record.plan_name or "Sem plano", "Ativo" if record.active else "Inativo"]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record.id)
                self.table.setItem(row, column, item)
        filtered = bool(self.search.text().strip() or self.letter or self.status.currentData() is not None)
        self.feedback.setText(f"{len(records)} aluno(s) encontrado(s)." if records else ("Nenhum aluno com esses filtros. Tente Limpar filtros." if filtered else "Seu primeiro aluno começa aqui. Clique em + Novo aluno."))

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
            profile = StudentProfile(student_id, self.service, self.plans, self)
            profile.changed.connect(self.on_changed)
            profile.exec()
        except Exception:
            logging.getLogger(__name__).exception("Falha ao abrir ficha")
            QMessageBox.warning(self, "Não foi possível abrir", "Atualize a lista e tente abrir a ficha novamente.")

    def on_changed(self) -> None:
        self.refresh()
        self.changed.emit()
