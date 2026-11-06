import logging
from datetime import datetime

from PySide6.QtCore import QDate, QLocale, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from studio_fd.services.dashboard_service import DashboardService, DashboardSummary
from studio_fd.utils.dates import parse_time
from studio_fd.utils.formatting import brl
from studio_fd.views import theme
from studio_fd.widgets.metric_card import MetricCard
from studio_fd.widgets.visuals import (
    Avatar, icon_button, icon_label, label, page_header, page_layout, panel, pill,
)

__all__ = ["DashboardView", "label"]


def greeting(hour: int) -> str:
    if hour < 12:
        return "Bom dia"
    return "Boa tarde" if hour < 18 else "Boa noite"


def clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            # Some da tela já; deleteLater só libera a memória depois.
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout():
            clear(item.layout())


class PlanBars(QWidget):
    """Barras horizontais simples: quantos alunos ativos em cada plano."""

    ROW = 44

    def __init__(self, formatter=str):
        super().__init__()
        self.rows: list[tuple[str, int]] = []
        self.formatter = formatter

    def set_rows(self, rows: list[tuple[str, int]]) -> None:
        self.rows = rows[:6]
        self.setMinimumHeight(max(1, len(self.rows)) * self.ROW)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(240, max(1, len(self.rows)) * self.ROW)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        top = max((count for _name, count in self.rows), default=1)
        font = QFont("Segoe UI")
        font.setPixelSize(13)
        for index, (name, count) in enumerate(self.rows):
            y = index * self.ROW
            painter.setFont(font)
            painter.setPen(QColor(theme.TEXT_2))
            painter.drawText(QRectF(0, y, self.width() - 124, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
            painter.setPen(QColor(theme.TEXT))
            painter.drawText(QRectF(self.width() - 120, y, 120, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.formatter(count))
            track = QRectF(0, y + 26, self.width(), 6)
            path = QPainterPath()
            path.addRoundedRect(track, 3, 3)
            painter.fillPath(path, QColor(theme.RAISED))
            fill = QPainterPath()
            fill.addRoundedRect(QRectF(0, y + 26, max(6, self.width() * count / top), 6), 3, 3)
            painter.fillPath(fill, QColor(theme.GOLD if index == 0 else "#8C7650"))


class DayAgenda(QWidget):
    """Agenda do dia em linhas compactas: horário | personal 1 | personal 2."""

    ROW = 34

    def __init__(self):
        super().__init__()
        self.rows: list[tuple[str, list[str | None]]] = []
        self.trainers: list[str] = []
        self.now_index = -1

    def set_rows(self, rows, trainers, now_index: int) -> None:
        self.rows, self.trainers, self.now_index = rows, trainers, now_index
        self.setMinimumHeight((len(rows) + 1) * self.ROW)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(400, (len(self.rows) + 1) * self.ROW)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        columns = max(1, len(self.trainers))
        time_width = 76
        width = (self.width() - time_width) / columns
        small = QFont("Segoe UI")
        small.setPixelSize(10)
        small.setWeight(QFont.Weight.DemiBold)
        painter.setFont(small)
        painter.setPen(QColor(theme.TEXT_3))
        painter.drawText(QRectF(0, 0, time_width, self.ROW - 8), Qt.AlignmentFlag.AlignVCenter, "HORÁRIO")
        for index, name in enumerate(self.trainers):
            painter.drawText(QRectF(time_width + index * width + 6, 0, width, self.ROW - 8), Qt.AlignmentFlag.AlignVCenter, name.upper())
        text_font = QFont("Segoe UI")
        text_font.setPixelSize(12)
        for row, (time, names) in enumerate(self.rows):
            y = (row + 1) * self.ROW
            now = row == self.now_index
            bold = QFont(text_font)
            bold.setWeight(QFont.Weight.DemiBold)
            painter.setFont(bold)
            painter.setPen(QColor(theme.GOLD if now else theme.TEXT_2))
            painter.drawText(QRectF(0, y, time_width, self.ROW - 6), Qt.AlignmentFlag.AlignVCenter, time + ("  •" if now else ""))
            for index, name in enumerate(names):
                cell = QRectF(time_width + index * width + 2, y + 2, width - 6, self.ROW - 8)
                path = QPainterPath()
                path.addRoundedRect(cell, 7, 7)
                if name:
                    painter.fillPath(path, QColor(theme.GOLD_TINT if now else theme.RAISED))
                    painter.setFont(bold)
                    painter.setPen(QColor(theme.TEXT))
                    text = painter.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, int(cell.width() - 20))
                    painter.drawText(cell.adjusted(10, 0, -6, 0), Qt.AlignmentFlag.AlignVCenter, text)
                else:
                    painter.setPen(QColor(theme.BORDER))
                    painter.drawPath(path)
                    painter.setFont(text_font)
                    painter.setPen(QColor(theme.TEXT_3))
                    painter.drawText(cell.adjusted(10, 0, -6, 0), Qt.AlignmentFlag.AlignVCenter, "Livre")


class DashboardView(QWidget):
    open_students = Signal()
    open_page = Signal(int)

    def __init__(self, service: DashboardService):
        super().__init__()
        self.service = service
        layout = page_layout(self)

        self.date_label = label("", "eyebrow")
        self.greeting_label = label("", "title")
        refresh = icon_button("Atualizar", "refresh", "ghostButton")
        refresh.setAccessibleName("Atualizar indicadores do Dashboard")
        refresh.clicked.connect(self.refresh)
        self.refresh_button = refresh
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(self.date_label)
        titles.addWidget(self.greeting_label)
        titles.addWidget(label("Um resumo do Studio com base nos cadastros de hoje."))
        header.addLayout(titles, 1)
        header.addWidget(refresh, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.active_card = MetricCard("Alunos ativos", "0", "", accent=True, icon_name="users")
        self.today_card = MetricCard("Agendados hoje", "0", "", icon_name="calendar")
        self.revenue_card = MetricCard("Recebido no mês", "R$ 0,00", "", icon_name="trend")
        self.due_card = MetricCard("Mensalidades atrasadas", "0", "", icon_name="clock")
        for column, card in enumerate((self.active_card, self.today_card, self.revenue_card, self.due_card)):
            grid.addWidget(card, 0, column)
            grid.setColumnStretch(column, 1)
        layout.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(14)
        due_panel, due_layout = panel()
        due_header = QHBoxLayout()
        due_header.addWidget(label("Próximos vencimentos", "sectionTitle"), 1)
        see_all = icon_button("Ver alunos", "arrow", "ghostButton")
        see_all.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        see_all.clicked.connect(self.open_students.emit)
        due_header.addWidget(see_all)
        due_layout.addLayout(due_header)
        self.due_list = QVBoxLayout()
        self.due_list.setSpacing(0)
        due_layout.addLayout(self.due_list)
        due_layout.addStretch()
        row.addWidget(due_panel, 3)

        plans_panel, plans_layout = panel()
        plans_layout.addWidget(label("Alunos por plano", "sectionTitle"))
        self.plan_bars = PlanBars()
        plans_layout.addWidget(self.plan_bars)
        self.plans_empty = label("Cadastre alunos com plano para ver a distribuição.", "caption")
        plans_layout.addWidget(self.plans_empty)
        plans_layout.addStretch()
        row.addWidget(plans_panel, 2)
        layout.addLayout(row)

        agenda, agenda_layout = panel(margins=(22, 18, 22, 18), spacing=12)
        agenda_top = QHBoxLayout()
        agenda_top.setSpacing(12)
        agenda_top.addWidget(icon_label("calendar", theme.GOLD, 18))
        agenda_top.addWidget(label("Agenda de hoje", "sectionTitle"))
        self.capacity = label("", "caption", wrap=False)
        agenda_top.addWidget(self.capacity)
        agenda_top.addStretch()
        open_agenda = icon_button("Abrir agenda", "arrow", "ghostButton")
        open_agenda.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        open_agenda.clicked.connect(lambda: self.open_page.emit(1))
        agenda_top.addWidget(open_agenda)
        agenda_layout.addLayout(agenda_top)
        self.day_agenda = DayAgenda()
        agenda_layout.addWidget(self.day_agenda)
        layout.addWidget(agenda)

        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        locale = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
        self.date_label.setText(locale.toString(QDate.currentDate(), "dddd, d 'de' MMMM").upper())
        self.greeting_label.setText(greeting(datetime.now().hour))
        try:
            summary = self.service.summary()
        except Exception:
            logging.getLogger(__name__).exception("Falha ao atualizar o Dashboard")
            self.active_card.set_value("—")
            self.feedback.setText("Não foi possível consultar os dados. Tente atualizar novamente; detalhes no log local.")
            return
        self.feedback.setText("")
        self.show_summary(summary)

    def show_summary(self, summary: DashboardSummary) -> None:
        inactive = max(0, summary.total_students - summary.active_students)
        self.active_card.set_value(str(summary.active_students),
                                   f"{inactive} inativo(s) no cadastro" if inactive else "Todos os cadastros ativos")
        self.today_card.set_value(str(summary.today_booked),
                                  f"{summary.today_capacity - summary.today_booked} vaga(s) livre(s) de {summary.today_capacity}")
        self.revenue_card.set_value(brl(summary.received_month_cents), f"Previsto: {brl(summary.monthly_revenue_cents)} em mensalidades")
        self.due_card.set_value(str(summary.overdue_count),
                                f"{brl(summary.overdue_cents)} em aberto" if summary.overdue_count else "Nenhuma em atraso")
        now = datetime.now()
        minutes = now.hour * 60 + now.minute
        times = [parse_time(time) for time, _names in summary.today_rows]
        now_index = max((index for index, value in enumerate(times) if value <= minutes), default=-1)
        if now_index == len(times) - 1 and times and minutes - times[-1] > 120:
            now_index = -1
        start = max(0, now_index - 1)
        visible = summary.today_rows[start:start + 8] or summary.today_rows[:8]
        self.day_agenda.set_rows(visible, summary.trainer_names, now_index - start if now_index >= 0 else -1)
        self.capacity.setText(f"{summary.today_booked} de {summary.today_capacity} vagas  ·  até {len(summary.trainer_names)} alunos por horário")

        clear(self.due_list)
        if not summary.upcoming:
            empty = label("Nenhum vencimento definido. Informe o dia do vencimento na ficha do aluno.", "caption")
            self.due_list.addWidget(empty)
        for item in summary.upcoming[:5]:
            line = QWidget()
            line.setMinimumHeight(54)
            content = QHBoxLayout(line)
            content.setContentsMargins(0, 8, 0, 8)
            content.setSpacing(12)
            content.addWidget(Avatar(item.name, 34))
            names = QVBoxLayout()
            names.setSpacing(1)
            names.addWidget(label(item.name, "strong", wrap=False))
            names.addWidget(label(item.plan_name or "Sem plano", "caption", wrap=False))
            content.addLayout(names, 1)
            values = QVBoxLayout()
            values.setSpacing(3)
            amount = label(brl(item.fee_cents) if item.fee_cents else "—", "strong", wrap=False)
            amount.setAlignment(Qt.AlignmentFlag.AlignRight)
            values.addWidget(amount)
            when = "Hoje" if item.days == 0 else ("Amanhã" if item.days == 1 else f"em {item.days} dias")
            tag = pill(f"Dia {item.due_date.day} · {when}", "gold" if item.days <= 3 else "muted")
            values.addWidget(tag, 0, Qt.AlignmentFlag.AlignRight)
            content.addLayout(values)
            self.due_list.addWidget(line)

        self.plan_bars.set_rows(summary.by_plan)
        self.plan_bars.setVisible(bool(summary.by_plan))
        self.plans_empty.setVisible(not summary.by_plan)
