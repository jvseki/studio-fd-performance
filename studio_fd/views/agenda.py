"""Agenda diária: um cartão por personal em cada horário.

O limite de alunos por horário é aplicado pelo AgendaService (e pelo banco);
esta tela apenas mostra as vagas e encaminha as ações.
"""

from datetime import date, datetime, timedelta
import logging

from PySide6.QtCore import QDate, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QGridLayout, QGroupBox, QHBoxLayout, QLineEdit,
    QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from studio_fd.services.agenda_service import STATUS_LABELS, AgendaService, SlotRow
from studio_fd.services.records import AppointmentRecord, TrainerRecord
from studio_fd.services.student_service import StudentService
from studio_fd.utils.dates import br_date, parse_time, week_start
from studio_fd.views import theme
from studio_fd.views.dashboard import clear
from studio_fd.widgets.controls import DateNavigator, HoverButtonCard, StudentPicker, WeekStrip, choose, font
from studio_fd.widgets.forms import FormDialog, form_layout
from studio_fd.widgets.motion import mix, toast
from studio_fd.widgets.visuals import icon_button, label, page_header, page_layout, panel, paint_avatar, pill
from studio_fd.widgets.icons import pixmap

STATUS_TONES = {"agendado": (theme.GOLD, theme.GOLD_TINT), "concluido": (theme.SUCCESS, theme.SUCCESS_TINT),
                "falta": (theme.DANGER, theme.DANGER_TINT)}


class SlotCard(HoverButtonCard):
    """Vaga de um personal em um horário: livre ou ocupada por um aluno."""

    def __init__(self, time: str, trainer: TrainerRecord, item: AppointmentRecord | None):
        super().__init__()
        self.time = time
        self.trainer = trainer
        self.item = item
        self.setFixedHeight(58)
        self.setMinimumWidth(180)
        name = item.student_name if item else "vaga livre"
        self.setAccessibleName(f"{time}, {trainer.name}: {name}")
        self.setToolTip("Clique para ver ações" if item else f"Agendar às {time} com {trainer.name}")

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        if self.item is None:
            painter.fillPath(path, mix("#00000000", theme.GOLD_TINT, self._hover))
            pen = QPen(mix(theme.BORDER_STRONG, theme.GOLD_LINE, self._hover), 1, Qt.PenStyle.DashLine)
            if self.hasFocus():
                pen = QPen(QColor(theme.GOLD), 1)
            painter.setPen(pen)
            painter.drawPath(path)
            painter.setFont(font(12, QFont.Weight.DemiBold if self._hover > .5 else QFont.Weight.Normal))
            if self._hover > .05:
                painter.setOpacity(self._hover)
                painter.drawPixmap(16, int(rect.height() / 2 - 8), pixmap("plus", theme.GOLD, 16))
                painter.setPen(QColor(theme.GOLD))
                painter.drawText(QRectF(40, 0, rect.width() - 50, rect.height()), Qt.AlignmentFlag.AlignVCenter, "Agendar aluno")
                painter.setOpacity(1 - self._hover)
            painter.setPen(QColor(theme.TEXT_3))
            painter.drawText(QRectF(16, 0, rect.width() - 30, rect.height()), Qt.AlignmentFlag.AlignVCenter, "Livre")
            return
        background, border = self.card_colors()
        painter.fillPath(path, background)
        painter.setPen(QPen(border, 1))
        painter.drawPath(path)
        accent, tint = STATUS_TONES.get(self.item.status, STATUS_TONES["agendado"])
        bar = QPainterPath()
        bar.addRoundedRect(QRectF(0, 12, 3, rect.height() - 24), 1.5, 1.5)
        painter.fillPath(bar, QColor(accent))
        paint_avatar(painter, QRectF(14, rect.height() / 2 - 16, 32, 32), self.item.student_name)
        status = STATUS_LABELS[self.item.status]
        status_font = font(11, QFont.Weight.DemiBold)
        status_width = painter.fontMetrics().horizontalAdvance(status) + 26
        name_area = QRectF(56, 0, rect.width() - 56 - status_width - 14, rect.height())
        painter.setFont(font(13, QFont.Weight.DemiBold))
        painter.setPen(QColor(theme.TEXT))
        painter.drawText(name_area, Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(self.item.student_name, Qt.TextElideMode.ElideRight, int(name_area.width())))
        painter.setFont(status_font)
        width = painter.fontMetrics().horizontalAdvance(status) + 20
        chip = QRectF(rect.width() - width - 12, rect.height() / 2 - 10, width, 20)
        chip_path = QPainterPath()
        chip_path.addRoundedRect(chip, 10, 10)
        painter.fillPath(chip_path, QColor(tint))
        painter.setPen(QColor(accent))
        painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, status)


class TimeLabel(QWidget):
    """Horário da linha, com destaque para a hora atual e marcação de lotado."""

    def __init__(self, time: str, now: bool, full: bool):
        super().__init__()
        self.time, self.now, self.full = time, now, full
        self.setFixedSize(92, 58)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(font(15, QFont.Weight.DemiBold))
        painter.setPen(QColor(theme.GOLD if self.now else theme.TEXT))
        painter.drawText(QRectF(0, 8, self.width(), 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.time)
        caption = "AGORA" if self.now else ("LOTADO" if self.full else "")
        if caption:
            painter.setFont(font(9, QFont.Weight.Bold))
            painter.setPen(QColor(theme.GOLD if self.now else theme.TEXT_3))
            painter.drawText(QRectF(0, 32, self.width(), 16), Qt.AlignmentFlag.AlignLeft, caption)
        if self.now:
            painter.setBrush(QColor(theme.GOLD))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(self.width() - 14, 16, 7, 7))


class BookingDialog(FormDialog):
    def __init__(self, agenda: AgendaService, students: StudentService, day: date, time: str | None = None,
                 trainer_id: int | None = None, parent=None, student_id: int | None = None):
        super().__init__("Agendar atendimento", "Agendar", parent,
                         f"Cada horário aceita até {len(agenda.settings.trainers(active_only=True))} alunos, um por personal.")
        self.agenda = agenda
        self.result = None
        self.resize(620, 600)
        group = QGroupBox("ATENDIMENTO")
        form = form_layout(group)
        self.student = StudentPicker(students.list(active=True), student_id)
        self.day = QDateEdit(QDate(day.year, day.month, day.day))
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat("dd/MM/yyyy")
        self.time = QComboBox()
        slots = agenda.settings.hours().slots()
        if time and time not in slots:
            slots = sorted({*slots, time}, key=parse_time)
        self.time.addItems(slots)
        if time:
            self.time.setCurrentText(time)
        self.trainer = QComboBox()
        self.trainer.addItem("Primeiro personal livre", None)
        for trainer in agenda.settings.trainers(active_only=True):
            self.trainer.addItem(trainer.name, trainer.id)
        if trainer_id is not None:
            self.trainer.setCurrentIndex(max(0, self.trainer.findData(trainer_id)))
        form.addRow("Aluno *", self.student)
        form.addRow("Data", self.day)
        form.addRow("Horário", self.time)
        form.addRow("Personal", self.trainer)
        self.body.addWidget(group)

        repeat = QGroupBox("HORÁRIO FIXO")
        repeat_form = form_layout(repeat)
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        self.repeat = QCheckBox("Repetir toda semana por")
        self.weeks = QSpinBox()
        self.weeks.setRange(1, 52)
        self.weeks.setValue(12)
        self.weeks.setSuffix(" semanas")
        self.weeks.setEnabled(False)
        self.repeat.toggled.connect(self.weeks.setEnabled)
        row_layout.addWidget(self.repeat)
        row_layout.addWidget(self.weeks, 1)
        repeat_form.addRow("", row)
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Opcional")
        self.notes.setMaxLength(200)
        repeat_form.addRow("Observação", self.notes)
        self.body.addWidget(repeat)
        self.body.addWidget(label("Semanas em que o horário estiver lotado são puladas e informadas no final.", "caption"))
        self.body.addStretch()
        self.save_button.clicked.connect(self.save)
        self.student.setFocus()

    def save(self) -> None:
        student_id = self.student.student_id()
        if student_id is None:
            self.feedback.setText("Escolha um aluno da lista.")
            return
        try:
            self.result = self.agenda.book(student_id, self.day.date().toPython(), self.time.currentText(),
                                           self.trainer.currentData(), self.weeks.value() - 1 if self.repeat.isChecked() else 0,
                                           self.notes.text())
        except Exception as error:
            self.show_error(error)
            return
        self.accept()


class AgendaView(QWidget):
    changed = Signal()
    open_student = Signal(int)

    def __init__(self, agenda: AgendaService, students: StudentService):
        super().__init__()
        self.agenda = agenda
        self.students = students
        self.current_row = None
        layout = page_layout(self)
        self.subtitle = label("")
        self.navigator = DateNavigator("day")
        self.navigator.changed.connect(lambda _day: self.refresh())
        create = icon_button("Agendar", "plus", "primaryButton")
        create.clicked.connect(lambda: self.book())
        header = page_header("OPERAÇÃO", "Agenda", self.subtitle, [create])
        layout.addLayout(header)
        tools = QHBoxLayout()
        tools.addWidget(self.navigator)
        tools.addStretch()
        layout.addLayout(tools)
        self.week = WeekStrip()
        self.week.selected.connect(self.navigator.set_value)
        layout.addWidget(self.week)

        card, body = panel(margins=(20, 16, 20, 18), spacing=10)
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(8)
        body.addLayout(self.grid)
        layout.addWidget(card)
        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        layout.addStretch()
        self.refresh()

    @property
    def day(self) -> date:
        return self.navigator.value

    def refresh(self) -> None:
        try:
            rows = self.agenda.day(self.day)
            occupancy = self.agenda.occupancy(week_start(self.day))
            trainers = self.agenda.settings.trainers(active_only=True)
        except Exception:
            logging.getLogger(__name__).exception("Falha ao carregar a agenda")
            self.feedback.setText("Não foi possível carregar a agenda. Troque de tela e volte para tentar novamente.")
            return
        self.week.set_days(occupancy, self.day)
        booked = sum(row.booked for row in rows)
        capacity = len(trainers) * len(rows)
        self.subtitle.setText(f"{booked} de {capacity} vagas ocupadas  ·  {len(trainers)} personais  ·  "
                              f"até {len(trainers)} alunos por horário")
        clear(self.grid)
        self.grid.addWidget(label("HORÁRIO", "fieldLabel", wrap=False), 0, 0)
        for column, trainer in enumerate(trainers, start=1):
            self.grid.addWidget(label(trainer.name.upper(), "fieldLabel", wrap=False), 0, column)
            self.grid.setColumnStretch(column, 1)
        now = datetime.now()
        minutes = now.hour * 60 + now.minute
        slot = self.agenda.settings.hours().slot_minutes
        self.current_row = None
        for index, row in enumerate(rows, start=1):
            is_now = self.day == date.today() and parse_time(row.time) <= minutes < parse_time(row.time) + slot
            time_label = TimeLabel(row.time, is_now, row.booked >= len(trainers) and bool(trainers))
            self.grid.addWidget(time_label, index, 0)
            if is_now:
                self.current_row = time_label
            for column, (trainer, item) in enumerate(row.cells, start=1):
                cell = SlotCard(row.time, trainer, item)
                cell.clicked.connect(lambda _=False, c=cell: self.activate(c))
                self.grid.addWidget(cell, index, column)
            if row.extra:
                names = ", ".join(f"{item.student_name} ({item.trainer_name})" for item in row.extra)
                self.grid.addWidget(label(f"Com personal inativo: {names}", "caption"), index, len(trainers) + 1)
        self.feedback.setText("" if rows else "Defina o horário de funcionamento em Configurações.")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(120, self.scroll_to_now)

    def scroll_to_now(self) -> None:
        parent = self.parentWidget()
        while parent is not None and not isinstance(parent, QScrollArea):
            parent = parent.parentWidget()
        if parent is not None and self.current_row is not None:
            parent.ensureWidgetVisible(self.current_row, 0, 160)

    def activate(self, cell: SlotCard) -> None:
        if cell.item is None:
            self.book(cell.time, cell.trainer.id)
            return
        item = cell.item
        actions = [("concluido", "Marcar como concluído", "check"), ("falta", "Marcar falta", "x")]
        if item.status != "agendado":
            actions.insert(0, ("agendado", "Voltar para agendado", "refresh"))
        actions += [("profile", "Abrir ficha do aluno", "user"), None,
                    ("remove", "Desmarcar este dia", "trash"),
                    ("remove_series", "Desmarcar este e os próximos", "repeat")]
        chosen = choose(self, [a for a in actions if a is None or a[0] != item.status])
        try:
            if chosen in STATUS_LABELS:
                self.agenda.set_status(item.id, chosen)
                toast(self, f"{item.student_name} · {STATUS_LABELS[chosen].lower()}")
            elif chosen == "profile":
                self.open_student.emit(item.student_id)
                return
            elif chosen == "remove":
                self.agenda.remove(item.id)
                toast(self, f"Horário de {item.student_name} desmarcado", "info")
            elif chosen == "remove_series":
                count = self.agenda.remove_future_series(item.id)
                toast(self, f"{count} horário(s) de {item.student_name} desmarcado(s)", "info")
            else:
                return
        except ValueError as error:
            toast(self, str(error), "error")
        self.refresh()
        self.changed.emit()

    def book(self, time: str | None = None, trainer_id: int | None = None) -> None:
        dialog = BookingDialog(self.agenda, self.students, self.day, time, trainer_id, self)
        if dialog.exec():
            result = dialog.result
            skipped = len(result.skipped)
            message = f"{len(result.created)} horário(s) agendado(s)"
            if skipped:
                message += f" · {skipped} semana(s) lotada(s) pulada(s)"
                details = "\n".join(f"{br_date(day)}: {reason}" for day, reason in result.skipped[:8])
                self.feedback.setText("Semanas não agendadas:\n" + details)
            toast(self, message, "info" if skipped else "success")
            if result.created[0] != self.day:
                self.navigator.set_value(result.created[0])
            self.refresh()
            self.changed.emit()
