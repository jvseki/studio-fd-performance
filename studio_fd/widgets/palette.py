"""Busca rápida (Ctrl+K): ir para telas, executar ações e abrir fichas de alunos."""

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import QDialog, QFrame, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from studio_fd.utils.formatting import search_key
from studio_fd.views import theme
from studio_fd.widgets.icons import icon
from studio_fd.widgets.visuals import label


class CommandPalette(QDialog):
    """entries = [(texto, detalhe, ícone, ação)] — a ação é chamada ao escolher."""

    def __init__(self, entries, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.entries = entries
        self.resize(620, 440)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setObjectName("paletteFrame")
        frame.setStyleSheet(f"QFrame#paletteFrame {{ background: {theme.RAISED}; border: 1px solid {theme.GOLD_LINE}; border-radius: 16px; }}"
                            f"QListWidget {{ background: transparent; border: none; outline: none; }}"
                            f"QListWidget::item {{ padding: 9px 10px; border-radius: 8px; color: {theme.TEXT}; }}"
                            f"QListWidget::item:selected {{ background: {theme.GOLD_TINT}; color: {theme.GOLD_HOVER}; }}"
                            f"QLineEdit {{ background: transparent; border: none; font-size: 16px; padding: 6px 4px; }}")
        outer.addWidget(frame)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Ir para tela, ação ou aluno...")
        self.search.addAction(icon("search", theme.GOLD, 18), QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(self.filter)
        self.search.installEventFilter(self)
        layout.addWidget(self.search)
        line = QFrame()
        line.setObjectName("divider")
        layout.addWidget(line)
        self.list = QListWidget()
        self.list.setIconSize(QSize(16, 16))
        self.list.itemActivated.connect(self.run)
        self.list.itemClicked.connect(self.run)
        layout.addWidget(self.list, 1)
        layout.addWidget(label("↑ ↓ para navegar  ·  Enter para abrir  ·  Esc para fechar", "caption"))
        self.filter("")

    def showEvent(self, event) -> None:
        parent = self.parentWidget()
        if parent is not None:
            center = parent.mapToGlobal(parent.rect().center())
            self.move(center.x() - self.width() // 2, parent.mapToGlobal(parent.rect().topLeft()).y() + 90)
        super().showEvent(event)
        self.search.setFocus()

    def filter(self, text: str) -> None:
        key = search_key(text.strip())
        self.list.clear()
        shown = 0
        for title, detail, icon_name, action in self.entries:
            if key and key not in search_key(f"{title} {detail}"):
                continue
            item = QListWidgetItem(icon(icon_name, theme.TEXT_2, 16), f"{title}    ·  {detail}" if detail else title)
            item.setData(Qt.ItemDataRole.UserRole, action)
            self.list.addItem(item)
            shown += 1
            if shown >= 60:
                break
        if self.list.count():
            self.list.setCurrentRow(0)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.search and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                step = 1 if event.key() == Qt.Key.Key_Down else -1
                self.list.setCurrentRow(max(0, min(self.list.count() - 1, self.list.currentRow() + step)))
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self.list.currentItem():
                    self.run(self.list.currentItem())
                return True
        return super().eventFilter(watched, event)

    def run(self, item: QListWidgetItem) -> None:
        action = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
        if action:
            action()
