"""Controles interativos compartilhados pelas telas."""

from datetime import date, timedelta

from PySide6.QtCore import QDate, QEasingCurve, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCalendarWidget, QComboBox, QCompleter, QHBoxLayout, QMenu, QPushButton, QWidget, QWidgetAction,
)

from studio_fd.utils.dates import WEEKDAYS_SHORT, add_months, first_of_month, long_date, month_label
from studio_fd.views import theme
from studio_fd.widgets.icons import icon
from studio_fd.widgets.motion import HoverMixin, mix


def font(size: int, weight=QFont.Weight.Normal) -> QFont:
    result = QFont("Segoe UI")
    result.setPixelSize(size)
    result.setWeight(weight)
    return result


def styled_menu(parent: QWidget | None = None) -> QMenu:
    """QMenu com cantos arredondados (o fundo translúcido permite o raio)."""
    menu = QMenu(parent)
    menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    return menu


def choose(parent: QWidget, items: list[tuple[str, str, str] | None], position=None) -> str | None:
    """Abre um menu de ações e devolve a chave escolhida.
    items = [(chave, texto, ícone) ou None para separador]."""
    menu = styled_menu(parent)
    actions = {}
    for item in items:
        if item is None:
            menu.addSeparator()
            continue
        key, text, icon_name = item
        tint = theme.DANGER if key.startswith("delete") or key.startswith("remove") else theme.TEXT_2
        action = menu.addAction(icon(icon_name, tint, 16), text)
        actions[action] = key
    chosen = menu.exec(position or QCursor.pos())
    return actions.get(chosen)


class SegmentedControl(QWidget):
    """Opções lado a lado com uma pílula que desliza até a escolhida."""

    changed = Signal(int)

    def __init__(self, options: list[str], index: int = 0):
        super().__init__()
        self.options = options
        self.index = index
        self.hovered = -1
        self._x = 0.0
        self.font_ = font(12, QFont.Weight.DemiBold)
        self.setFixedHeight(36)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(260)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._move)

    def _move(self, value) -> None:
        self._x = float(value)
        self.update()

    def segment_width(self) -> float:
        return (self.width() - 8) / max(1, len(self.options))

    def sizeHint(self) -> QSize:
        widest = max(self.fontMetrics().horizontalAdvance(text) for text in self.options)
        return QSize(int((widest + 34) * len(self.options) + 8), 36)

    def set_index(self, index: int, animate: bool = True) -> None:
        if not 0 <= index < len(self.options):
            return
        target = index * self.segment_width()
        if animate and self.isVisible():
            self.animation.stop()
            self.animation.setStartValue(self._x)
            self.animation.setEndValue(target)
            self.animation.start()
        else:
            self._x = target
        if index != self.index:
            self.index = index
            self.changed.emit(index)
        self.update()

    def resizeEvent(self, event) -> None:
        self._x = self.index * self.segment_width()
        super().resizeEvent(event)

    def mouseMoveEvent(self, event) -> None:
        hovered = int((event.position().x() - 4) // self.segment_width())
        if hovered != self.hovered:
            self.hovered = hovered
            self.update()

    def leaveEvent(self, event) -> None:
        self.hovered = -1
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_index(int((event.position().x() - 4) // self.segment_width()))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Right:
            self.set_index(min(len(self.options) - 1, self.index + 1))
        elif event.key() == Qt.Key.Key_Left:
            self.set_index(max(0, self.index - 1))
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outer = QPainterPath()
        outer.addRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 10, 10)
        painter.fillPath(outer, QColor(theme.SURFACE))
        painter.setPen(QPen(QColor(theme.GOLD if self.hasFocus() else theme.BORDER), 1))
        painter.drawPath(outer)
        width = self.segment_width()
        pill = QPainterPath()
        pill.addRoundedRect(QRectF(4 + self._x, 4, width, self.height() - 8), 7, 7)
        painter.fillPath(pill, QColor(theme.RAISED))
        painter.setPen(QPen(QColor(theme.BORDER_STRONG), 1))
        painter.drawPath(pill)
        painter.setFont(self.font_)
        for index, text in enumerate(self.options):
            color = theme.GOLD if index == self.index else (theme.TEXT if index == self.hovered else theme.TEXT_2)
            painter.setPen(QColor(color))
            painter.drawText(QRectF(4 + index * width, 0, width, self.height()), Qt.AlignmentFlag.AlignCenter, text)


class DateNavigator(QWidget):
    """◀  quinta-feira, 5 de novembro  ▶   Hoje — por dia ou por mês."""

    changed = Signal(object)

    def __init__(self, mode: str = "day", value: date | None = None):
        super().__init__()
        self.mode = mode
        self.value = first_of_month(value or date.today()) if mode == "month" else (value or date.today())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.previous = self._arrow("chevron-left", "Anterior")
        self.label = QPushButton()
        self.label.setObjectName("dateLabel")
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label.setMinimumWidth(240 if mode == "day" else 170)
        self.label.clicked.connect(self.open_calendar)
        self.following = self._arrow("chevron-right", "Próximo")
        self.today = QPushButton("Hoje" if mode == "day" else "Este mês")
        self.today.setObjectName("ghostButton")
        self.today.setCursor(Qt.CursorShape.PointingHandCursor)
        self.today.clicked.connect(lambda: self.set_value(date.today()))
        self.previous.clicked.connect(lambda: self.step(-1))
        self.following.clicked.connect(lambda: self.step(1))
        for widget in (self.previous, self.label, self.following, self.today):
            layout.addWidget(widget)
        self._render()

    def _arrow(self, name: str, tip: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("iconButton")
        button.setIcon(icon(name, theme.TEXT_2, 16))
        button.setFixedSize(34, 34)
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _render(self) -> None:
        if self.mode == "day":
            prefix = "Hoje · " if self.value == date.today() else ""
            self.label.setText(prefix + long_date(self.value))
            self.today.setEnabled(self.value != date.today())
        else:
            self.label.setText(month_label(self.value))
            self.today.setEnabled(self.value != first_of_month(date.today()))

    def step(self, amount: int) -> None:
        self.set_value(self.value + timedelta(days=amount) if self.mode == "day" else add_months(self.value, amount))

    def set_value(self, value: date) -> None:
        value = first_of_month(value) if self.mode == "month" else value
        if value != self.value:
            self.value = value
            self._render()
            self.changed.emit(value)

    def open_calendar(self) -> None:
        if self.mode != "day":
            return
        menu = styled_menu(self)
        calendar = QCalendarWidget()
        calendar.setGridVisible(False)
        calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        calendar.setSelectedDate(QDate(self.value.year, self.value.month, self.value.day))
        calendar.setMinimumSize(300, 240)
        holder = QWidgetAction(menu)
        holder.setDefaultWidget(calendar)
        menu.addAction(holder)
        calendar.clicked.connect(lambda chosen: (self.set_value(chosen.toPython()), menu.close()))
        menu.exec(self.label.mapToGlobal(self.label.rect().bottomLeft()))


class WeekStrip(QWidget):
    """Sete dias com barra de ocupação. Clicar escolhe o dia."""

    selected = Signal(object)

    def __init__(self):
        super().__init__()
        self.days: list[tuple[date, int, int]] = []
        self.current = date.today()
        self.hovered = -1
        self.setFixedHeight(74)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_days(self, occupancy: dict[date, tuple[int, int]], current: date) -> None:
        self.days = [(day, used, total) for day, (used, total) in sorted(occupancy.items())]
        self.current = current
        self.update()

    def _cell(self, index: int) -> QRectF:
        width = (self.width() - 6 * 8) / 7
        return QRectF(index * (width + 8), 0, width, self.height())

    def mouseMoveEvent(self, event) -> None:
        hovered = next((index for index in range(len(self.days)) if self._cell(index).contains(event.position())), -1)
        if hovered != self.hovered:
            self.hovered = hovered
            self.update()

    def leaveEvent(self, event) -> None:
        self.hovered = -1
        self.update()

    def mousePressEvent(self, event) -> None:
        for index, (day, _used, _total) in enumerate(self.days):
            if self._cell(index).contains(event.position()):
                self.selected.emit(day)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        today = date.today()
        for index, (day, used, total) in enumerate(self.days):
            rect = self._cell(index).adjusted(.5, .5, -.5, -.5)
            chosen = day == self.current
            path = QPainterPath()
            path.addRoundedRect(rect, 12, 12)
            background = theme.GOLD_TINT if chosen else (theme.RAISED if index == self.hovered else theme.SURFACE)
            painter.fillPath(path, QColor(background))
            painter.setPen(QPen(QColor(theme.GOLD_LINE if chosen else theme.BORDER), 1))
            painter.drawPath(path)
            painter.setFont(font(10, QFont.Weight.DemiBold))
            painter.setPen(QColor(theme.GOLD if chosen else theme.TEXT_3))
            painter.drawText(QRectF(rect.left() + 14, rect.top() + 10, rect.width(), 14), Qt.AlignmentFlag.AlignLeft,
                             WEEKDAYS_SHORT[day.weekday()] + ("  ·  HOJE" if day == today else ""))
            painter.setFont(font(20, QFont.Weight.DemiBold))
            painter.setPen(QColor(theme.TEXT if chosen or index == self.hovered else theme.TEXT_2))
            painter.drawText(QRectF(rect.left() + 14, rect.top() + 26, 60, 28), Qt.AlignmentFlag.AlignLeft, str(day.day))
            painter.setFont(font(11))
            painter.setPen(QColor(theme.TEXT_3))
            painter.drawText(QRectF(rect.left(), rect.top() + 30, rect.width() - 14, 22),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{used}/{total}" if total else "")
            track = QRectF(rect.left() + 14, rect.bottom() - 12, rect.width() - 28, 4)
            bar = QPainterPath()
            bar.addRoundedRect(track, 2, 2)
            painter.fillPath(bar, QColor(theme.BORDER))
            if total and used:
                fill = QPainterPath()
                fill.addRoundedRect(QRectF(track.left(), track.top(), max(4, track.width() * min(1, used / total)), 4), 2, 2)
                painter.fillPath(fill, QColor(theme.GOLD if chosen else "#8C7650"))


class StudentPicker(QComboBox):
    """Lista de alunos com pesquisa ao digitar (contém, sem diferenciar maiúsculas)."""

    def __init__(self, students: list, selected: int | None = None):
        super().__init__()
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.lineEdit().setPlaceholderText("Digite para pesquisar o aluno...")
        for student in students:
            self.addItem(student.full_name, student.id)
        completer = QCompleter(self.model(), self)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.popup().setObjectName("completerPopup")
        self.setCompleter(completer)
        self.setCurrentIndex(self.findData(selected) if selected is not None else -1)
        if selected is None:
            self.lineEdit().clear()

    def student_id(self) -> int | None:
        index = self.findText(self.currentText().strip(), Qt.MatchFlag.MatchFixedString)
        return self.itemData(index) if index >= 0 else None


class HoverButtonCard(HoverMixin, QWidget):
    """Base para cartões clicáveis pintados à mão, com hover animado."""

    clicked = Signal()

    def __init__(self):
        super().__init__()
        self._setup_hover()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)

    def card_colors(self, active: bool = False) -> tuple[QColor, QColor]:
        background = mix(theme.SURFACE, theme.RAISED, self._hover)
        border = mix(theme.BORDER, theme.GOLD_LINE, self._hover if not active else 1)
        if self.hasFocus():
            border = QColor(theme.GOLD)
        return background, border
