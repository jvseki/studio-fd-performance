"""Backup: exportar um arquivo único e restaurar com validação completa."""

import logging
from pathlib import Path

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from studio_fd.services.backup_service import EXTENSION, BackupService
from studio_fd.views import theme
from studio_fd.widgets.controls import choose
from studio_fd.widgets.data_table import DataTable
from studio_fd.widgets.motion import toast
from studio_fd.widgets.visuals import icon_button, icon_label, label, page_header, page_layout, panel

REASONS = {"manual": "Manual", "automatic": "Automático", "before-update": "Antes de atualizar", "before-restore": "Antes de restaurar"}


def size_text(size: int) -> str:
    return f"{size / 1024 / 1024:.1f} MB" if size >= 1024 * 1024 else f"{max(1, size // 1024)} KB"


class BackupView(QWidget):
    restart_requested = Signal()

    def __init__(self, service: BackupService):
        super().__init__()
        self.service = service
        self.files = {}
        layout = page_layout(self)
        folder = icon_button("Abrir pasta", "folder", "ghostButton")
        folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(service.paths.backups))))
        layout.addLayout(page_header("SISTEMA", "Backup", label(
            "Um único arquivo com alunos, pagamentos, agenda, contratos e configurações. "
            "Guarde uma cópia em pen drive ou na nuvem."), [folder]))

        row = QHBoxLayout()
        row.setSpacing(14)
        for title, text, icon_name, button_text, role, slot in (
            ("Exportar backup completo", "Gera um arquivo .fdbkp verificado, pronto para levar a outro computador.",
             "download", "Exportar agora", "primaryButton", self.export),
            ("Restaurar backup", "Valida o arquivo, guarda uma cópia dos dados atuais e reabre o Studio com os dados do backup.",
             "upload", "Escolher arquivo", "", self.restore),
        ):
            card, body = panel("heroPanel" if role else "panel", (24, 22, 24, 22), 10)
            body.addWidget(icon_label(icon_name, theme.GOLD, 26))
            body.addWidget(label(title, "sectionTitle"))
            body.addWidget(label(text))
            body.addStretch()
            button = icon_button(button_text, icon_name, role)
            button.clicked.connect(slot)
            body.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
            card.setMinimumHeight(200)
            row.addWidget(card, 1)
        layout.addLayout(row)

        history, history_layout = panel(margins=(0, 16, 0, 0), spacing=8)
        top = QVBoxLayout()
        top.setContentsMargins(20, 0, 20, 0)
        top.addWidget(label("Cópias neste computador", "sectionTitle"))
        top.addWidget(label("O Studio faz um backup automático por dia ao abrir e guarda os 10 mais recentes.", "caption"))
        history_layout.addLayout(top)
        self.table = DataTable(["Arquivo", "Tipo", "Data", "Tamanho"], [3.4, 1.4, 1.4, 0.9], 50)
        self.table.setMinimumHeight(300)
        self.table.cellClicked.connect(lambda row, _c: self.actions(self.table.key(row)))
        self.table.row_menu.connect(lambda key, _p: self.actions(key))
        history_layout.addWidget(self.table)
        layout.addWidget(history, 1)
        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        self.refresh()

    def refresh(self) -> None:
        try:
            files = self.service.list_backups()
        except OSError:
            logging.getLogger(__name__).exception("Falha ao listar backups")
            files = []
        self.files = {str(item.path): item for item in files}
        self.table.set_rows([(str(item.path), [
            (item.path.name, "strong"), ("Automático" if item.automatic else ("Antes de atualizar" if item.path.suffix == ".zip" else "Manual"),
                                          "pill:muted" if item.automatic else "pill:gold"),
            (item.modified.strftime("%d/%m/%Y %H:%M"), "muted"), (size_text(item.size), "muted"),
        ]) for item in files])

    def export(self) -> None:
        suggestion = str(Path.home() / "Documents" / self.service.default_name())
        path, _ = QFileDialog.getSaveFileName(self, "Salvar backup", suggestion, f"Backup Studio FD (*{EXTENSION})")
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.service.export(Path(path))
        except Exception as error:
            logging.getLogger(__name__).exception("Falha ao exportar backup")
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Backup não concluído", str(error) if isinstance(error, ValueError) else
                                "Não foi possível salvar o arquivo. Confira o espaço e a pasta escolhida.")
            return
        QApplication.restoreOverrideCursor()
        toast(self, f"Backup salvo: {result.name}")
        self.feedback.setText(f"Último backup exportado: {result}")

    def restore(self, path: str | None = None) -> None:
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Escolher backup", str(Path.home() / "Documents"),
                                                  f"Backup Studio FD (*{EXTENSION} *.zip)")
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            info = self.service.inspect(Path(path))
        except Exception as error:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Backup recusado", str(error) if isinstance(error, ValueError) else
                                "Não foi possível ler esse arquivo.")
            return
        QApplication.restoreOverrideCursor()
        created = info.created_at.astimezone().strftime("%d/%m/%Y às %H:%M") if info.created_at else "data desconhecida"
        counts = "\n".join(f"  • {value} {name}" for name, value in info.counts.items())
        answer = QMessageBox.question(
            self, "Restaurar este backup?",
            f"Backup válido, criado em {created} (versão {info.app_version or '?'}).\n\n{counts}\n  • {info.files} PDF(s) de contrato\n\n"
            "Os dados atuais serão substituídos. Antes disso, uma cópia deles será salva na pasta backups.\n"
            "O Studio será reaberto para concluir.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            safety = self.service.stage_restore(Path(path))
        except Exception as error:
            logging.getLogger(__name__).exception("Falha ao preparar restauração")
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Restauração não iniciada", (str(error) if isinstance(error, ValueError) else
                                "Não foi possível preparar a restauração.") + "\nSeus dados atuais não foram alterados.")
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Pronto para restaurar",
                                f"Cópia dos dados atuais salva em:\n{safety}\n\nO Studio vai fechar e abrir novamente com o backup.")
        self.restart_requested.emit()

    def actions(self, key) -> None:
        item = self.files.get(key)
        if item is None:
            return
        chosen = choose(self, [("restore", "Restaurar esta cópia", "upload"), ("folder", "Mostrar na pasta", "folder")])
        if chosen == "restore":
            self.restore(str(item.path))
        elif chosen == "folder":
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(item.path.parent)))
