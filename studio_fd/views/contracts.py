"""Contratos: anexar o PDF à ficha do aluno e abri-lo no programa padrão do Windows."""

from datetime import date
import logging
from pathlib import Path

from PySide6.QtCore import QDate, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QFileDialog, QGroupBox, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QWidget,
)

from studio_fd.services.contract_service import SIGNATURES, ContractService
from studio_fd.services.records import ContractRecord
from studio_fd.services.student_service import StudentService
from studio_fd.utils.dates import br_date
from studio_fd.views import theme
from studio_fd.widgets.controls import StudentPicker, choose
from studio_fd.widgets.data_table import DataTable
from studio_fd.widgets.forms import FormDialog, form_layout
from studio_fd.widgets.icons import icon
from studio_fd.widgets.motion import toast
from studio_fd.widgets.visuals import icon_button, label, page_header, page_layout, panel


def open_contract(parent, service: ContractService, record: ContractRecord) -> None:
    try:
        target = service.file(record)
    except ValueError as error:
        toast(parent, str(error), "error")
        return
    if target is None or not target.exists():
        toast(parent, "Este contrato não tem PDF anexado.", "error")
        return
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(target))):
        toast(parent, "Não foi possível abrir o PDF. Instale um leitor de PDF.", "error")


class ContractDialog(FormDialog):
    def __init__(self, service: ContractService, students: StudentService, student_id: int | None = None, parent=None):
        super().__init__("Anexar contrato", "Salvar contrato", parent,
                         "O PDF é copiado para a pasta de dados do Studio e entra no backup.")
        self.service = service
        self.saved = None
        self.pdf: Path | None = None
        self.resize(620, 560)
        group = QGroupBox("CONTRATO")
        form = form_layout(group)
        self.student = StudentPicker(students.list(), student_id)
        self.signature = QComboBox()
        for key, text in SIGNATURES.items():
            self.signature.addItem(text, key)
        self.signed_on = QDateEdit(QDate.currentDate())
        self.signed_on.setCalendarPopup(True)
        self.signed_on.setDisplayFormat("dd/MM/yyyy")
        self.signed_on.setMaximumDate(QDate.currentDate())
        file_row = QWidget()
        row = QHBoxLayout(file_row)
        row.setContentsMargins(0, 0, 0, 0)
        self.file_label = label("Nenhum arquivo escolhido", "caption", wrap=False)
        choose_file = QPushButton("Escolher PDF")
        choose_file.setIcon(icon("file", theme.TEXT_2, 16))
        choose_file.setAutoDefault(False)
        choose_file.clicked.connect(self.pick)
        row.addWidget(choose_file)
        row.addWidget(self.file_label, 1)
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Opcional")
        form.addRow("Aluno *", self.student)
        form.addRow("Assinatura", self.signature)
        form.addRow("Data", self.signed_on)
        form.addRow("Arquivo", file_row)
        form.addRow("Observação", self.notes)
        self.body.addWidget(group)
        self.body.addWidget(label("Sem PDF, o contrato fica registrado apenas com tipo e data da assinatura.", "caption"))
        self.body.addStretch()
        self.save_button.clicked.connect(self.save)

    def pick(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Escolher contrato", str(Path.home()), "PDF (*.pdf)")
        if path:
            self.pdf = Path(path)
            self.file_label.setText(self.pdf.name)

    def save(self) -> None:
        student_id = self.student.student_id()
        if student_id is None:
            self.feedback.setText("Escolha um aluno da lista.")
            return
        try:
            self.saved = self.service.add(student_id, self.signature.currentData(), self.signed_on.date().toPython(),
                                          self.pdf, self.notes.text())
        except Exception as error:
            self.show_error(error)
            return
        self.accept()


class ContractsView(QWidget):
    changed = Signal()
    open_student = Signal(int)

    def __init__(self, service: ContractService, students: StudentService):
        super().__init__()
        self.service, self.students = service, students
        self.records: dict[int, ContractRecord] = {}
        layout = page_layout(self)
        add = icon_button("Anexar contrato", "plus", "primaryButton")
        add.clicked.connect(self.add)
        self.subtitle = label("")
        layout.addLayout(page_header("CADASTROS", "Contratos", self.subtitle, [add]))
        card, body = panel(margins=(0, 0, 0, 0), spacing=0)
        tools = QHBoxLayout()
        tools.setContentsMargins(18, 16, 18, 10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Pesquisar pelo nome do aluno...")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icon("search", theme.TEXT_3, 16), QLineEdit.ActionPosition.LeadingPosition)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(180)
        self.timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda _t: self.timer.start())
        tools.addWidget(self.search)
        body.addLayout(tools)
        self.table = DataTable(["Aluno", "Assinatura", "Data", "Arquivo", "Observação"], [3, 1.3, 1.2, 1.3, 2.2])
        self.table.setMinimumHeight(380)
        self.table.cellClicked.connect(lambda row, _c: self.actions(self.table.key(row)))
        self.table.row_menu.connect(lambda key, _p: self.actions(key))
        body.addWidget(self.table)
        layout.addWidget(card, 1)
        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        self.refresh()

    def refresh(self) -> None:
        try:
            records = self.service.list(self.search.text())
        except Exception:
            logging.getLogger(__name__).exception("Falha ao carregar contratos")
            self.feedback.setText("Não foi possível carregar os contratos.")
            return
        self.records = {item.id: item for item in records}
        self.subtitle.setText(f"{len(records)} contrato(s)  ·  clique para abrir o PDF")
        self.table.set_rows([(item.id, [
            (item.student_name, "avatar"), (SIGNATURES[item.signature_type], "pill:gold" if item.signature_type == "online" else "pill:muted"),
            (br_date(item.signed_on), "muted"), ("PDF anexado" if item.file_path else "Sem arquivo", "pill:success" if item.file_path else "pill:muted"),
            (item.notes or "—", "muted"),
        ]) for item in records])
        self.feedback.setText("" if records else "Nenhum contrato registrado. Use Anexar contrato.")

    def add(self, student_id: int | None = None) -> None:
        if ContractDialog(self.service, self.students, student_id, self).exec():
            toast(self, "Contrato salvo")
            self.refresh()
            self.changed.emit()

    def actions(self, contract_id) -> None:
        record = self.records.get(contract_id)
        if record is None:
            return
        items = [("open", "Abrir contrato", "external")] if record.file_path else []
        items += [("profile", "Abrir ficha do aluno", "user"), None, ("delete", "Excluir contrato", "trash")]
        chosen = choose(self, items)
        if chosen == "open":
            open_contract(self, self.service, record)
        elif chosen == "profile":
            self.open_student.emit(record.student_id)
        elif chosen == "delete":
            if QMessageBox.question(self, "Excluir contrato", f"Excluir o contrato de {record.student_name}? "
                                    "O PDF vai para a pasta contratos/_removidos.") == QMessageBox.StandardButton.Yes:
                self.service.delete(record.id)
                toast(self, "Contrato excluído", "info")
                self.refresh()
                self.changed.emit()
