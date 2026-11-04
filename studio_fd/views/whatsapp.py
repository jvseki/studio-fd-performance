from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QTextEdit

from studio_fd.services.records import StudentRecord
from studio_fd.services.whatsapp_service import chat_url, greeting
from studio_fd.utils.formatting import display_phone
from studio_fd.views.dashboard import label
from studio_fd.widgets.forms import FormDialog


class WhatsAppDialog(FormDialog):
    def __init__(self, student: StudentRecord, parent=None):
        super().__init__("Mensagem pelo WhatsApp", "Abrir conversa no WhatsApp", parent)
        self.student = student
        self.resize(620, 460)
        recipient = label(f"Para: {student.full_name}\n{display_phone(student.phone)}", "sectionTitle")
        recipient.setTextFormat(Qt.TextFormat.PlainText)
        self.body.addWidget(recipient)
        self.message = QTextEdit()
        self.message.setAcceptRichText(False)
        self.message.setPlainText(greeting(student.full_name))
        self.body.addWidget(self.message, 1)
        self.body.addWidget(label("Revise o texto. A conversa será aberta no aplicativo ou navegador; você envia a mensagem pelo WhatsApp. É necessário estar conectado à internet.", "caption"))
        self.save_button.clicked.connect(self.open_chat)

    def open_chat(self) -> None:
        try:
            url = chat_url(self.student.phone, self.message.toPlainText())
            if not QDesktopServices.openUrl(QUrl(url)):
                raise ValueError("Não foi possível abrir o WhatsApp. Confira o navegador padrão e tente novamente.")
        except Exception as error:
            self.show_error(error)
            return
        self.accept()
