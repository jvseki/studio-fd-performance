"""Tabela de leitura: linhas espaçadas, sem grade, com avatar e etiquetas.

Cada célula guarda o texto normal (para pesquisa e testes) e um "papel"
visual em ROLE_STYLE: strong, muted, avatar ou pill:<tom>.
"""

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QStyledItemDelegate, QTableWidget, QTableWidgetItem

from studio_fd.views import theme
from studio_fd.widgets.motion import smooth
from studio_fd.widgets.visuals import paint_avatar

ROLE_STYLE = Qt.ItemDataRole.UserRole + 1
PILL_TONES = {
    "success": ("#16231B", "#23392A", theme.SUCCESS),
    "muted": (theme.RAISED, theme.BORDER, theme.TEXT_3),
    "gold": (theme.GOLD_TINT, theme.GOLD_LINE, theme.GOLD),
    "danger": (theme.DANGER_TINT, theme.DANGER_LINE, theme.DANGER),
}


class RowDelegate(QStyledItemDelegate):
    def __init__(self, table: "DataTable"):
        super().__init__(table)
        self.table = table

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(option.rect)
        if self.table.selectionModel().isRowSelected(index.row(), index.parent()):
            painter.fillRect(rect, QColor(theme.GOLD_TINT))
        elif index.row() == self.table.hovered_row:
            painter.fillRect(rect, QColor("#17171B"))
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        line_y = rect.bottom() - .5
        painter.drawLine(QPointF(rect.left(), line_y), QPointF(rect.right(), line_y))
        text = index.data() or ""
        style = index.data(ROLE_STYLE) or ""
        content = rect.adjusted(16, 0, -12, 0)
        font = QFont(option.font)
        font.setPixelSize(13)
        color = theme.TEXT
        if style == "avatar":
            size = 30
            paint_avatar(painter, QRectF(content.left(), content.center().y() - size / 2, size, size), text)
            content.setLeft(content.left() + size + 12)
            font.setWeight(QFont.Weight.DemiBold)
        elif style == "strong":
            font.setWeight(QFont.Weight.DemiBold)
        elif style == "muted":
            color = theme.TEXT_2
        elif style in ("income", "expense"):
            font.setWeight(QFont.Weight.DemiBold)
            color = theme.SUCCESS if style == "income" else theme.DANGER
        if style.startswith("pill:"):
            background, border, foreground = PILL_TONES.get(style[5:], PILL_TONES["muted"])
            font.setPixelSize(11)
            font.setWeight(QFont.Weight.DemiBold)
            metrics = QFontMetrics(font)
            width = metrics.horizontalAdvance(text) + 20
            box = QRectF(content.left(), content.center().y() - 10, width, 20)
            path = QPainterPath()
            path.addRoundedRect(box.adjusted(.5, .5, -.5, -.5), 10, 10)
            painter.setPen(QPen(QColor(border), 1))
            painter.setBrush(QColor(background))
            painter.drawPath(path)
            painter.setFont(font)
            painter.setPen(QColor(foreground))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
        else:
            painter.setFont(font)
            painter.setPen(QColor(color))
            elided = QFontMetrics(font).elidedText(text, Qt.TextElideMode.ElideRight, int(content.width()))
            painter.drawText(content, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)
        painter.restore()


class DataTable(QTableWidget):
    row_menu = Signal(object, QPoint)  # (chave da linha, posição global) no clique direito

    def __init__(self, headers: list[str], ratios: list[float], row_height: int = 56):
        super().__init__(0, len(headers))
        self.ratios = ratios
        self.hovered_row = -1
        self.setHorizontalHeaderLabels([header.upper() for header in headers])
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setHighlightSections(False)
        header.setFixedHeight(38)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(row_height)
        self.setShowGrid(False)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setItemDelegate(RowDelegate(self))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        smooth(self)

    def key(self, row: int):
        item = self.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _context_menu(self, position) -> None:
        row = self.rowAt(position.y())
        if row >= 0:
            self.selectRow(row)
            self.row_menu.emit(self.key(row), self.viewport().mapToGlobal(position))

    def set_rows(self, rows: list[tuple[object, list[tuple[str, str]]]]) -> None:
        """rows = [(id, [(texto, papel), ...]), ...]"""
        self.hovered_row = -1
        self.setRowCount(len(rows))
        for row, (key, cells) in enumerate(rows):
            for column, (text, style) in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, key)
                item.setData(ROLE_STYLE, style)
                self.setItem(row, column, item)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        available = self.viewport().width()
        total = sum(self.ratios)
        used = 0
        for column, ratio in enumerate(self.ratios):
            width = available - used if column == len(self.ratios) - 1 else int(available * ratio / total)
            self.setColumnWidth(column, width)
            used += width

    def mouseMoveEvent(self, event) -> None:
        row = self.rowAt(event.position().toPoint().y())
        if row != self.hovered_row:
            self.hovered_row = row
            self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.hovered_row = -1
        self.viewport().update()
        super().leaveEvent(event)
