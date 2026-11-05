from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QTextEdit, QVBoxLayout

from studio_fd.services.records import StudentRecord
from studio_fd.services.whatsapp_service import chat_url, greeting
from studio_fd.utils.formatting import display_phone
from studio_fd.views import theme
from studio_fd.widgets.forms import FormDialog
from studio_fd.widgets.icons import icon
from studio_fd.widgets.visuals import Avatar, icon_label, label


class WhatsAppDialog(FormDialog):
    def __init__(self, student: StudentRecord, parent=None):
        super().__init__("Mensagem pelo WhatsApp", "Abrir no WhatsApp", parent,
                         "Revise o texto. O envio acontece no seu WhatsApp, nunca automaticamente.")
        self.student = student
        self.resize(620, 520)
        self.save_button.setIcon(icon("message", theme.GOLD_INK, 16))
        recipient = QFrame()
        recipient.setObjectName("recipient")
        row = QHBoxLayout(recipient)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)
        row.addWidget(Avatar(student.full_name, 38))
        names = QVBoxLayout()
        names.setSpacing(1)
        name = label(student.full_name, "strong", wrap=False)
        name.setTextFormat(Qt.TextFormat.PlainText)
        names.addWidget(name)
        names.addWidget(label(display_phone(student.phone), "caption", wrap=False))
        row.addLayout(names, 1)
        self.body.addSpacing(12)
        self.body.addWidget(recipient)
        self.body.addSpacing(12)
        self.message = QTextEdit()
        self.message.setAcceptRichText(False)
        self.message.setMinimumHeight(170)
        self.message.setPlainText(greeting(student.full_name))
        self.body.addWidget(self.message, 1)
        self.body.addSpacing(8)
        hint = QHBoxLayout()
        hint.setSpacing(8)
        hint.addWidget(icon_label("info", theme.TEXT_3, 14), 0, Qt.AlignmentFlag.AlignTop)
        hint.addWidget(label("A conversa abre no aplicativo ou no navegador. É preciso estar conectado à internet.", "caption"), 1)
        self.body.addLayout(hint)
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
