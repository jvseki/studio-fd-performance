import logging
from datetime import datetime

from PySide6.QtCore import QDate, QLocale, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from studio_fd.services.dashboard_service import DashboardService, DashboardSummary
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

    def __init__(self):
        super().__init__()
        self.rows: list[tuple[str, int]] = []

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
            painter.drawText(QRectF(0, y, self.width() - 40, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
            painter.setPen(QColor(theme.TEXT))
            painter.drawText(QRectF(self.width() - 40, y, 40, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(count))
            track = QRectF(0, y + 26, self.width(), 6)
            path = QPainterPath()
            path.addRoundedRect(track, 3, 3)
            painter.fillPath(path, QColor(theme.RAISED))
            fill = QPainterPath()
            fill.addRoundedRect(QRectF(0, y + 26, max(6, self.width() * count / top), 6), 3, 3)
            painter.fillPath(fill, QColor(theme.GOLD if index == 0 else "#8C7650"))


class DashboardView(QWidget):
    open_students = Signal()

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
        self.revenue_card = MetricCard("Receita mensal prevista", "R$ 0,00", "Soma das mensalidades combinadas", icon_name="trend")
        self.ticket_card = MetricCard("Ticket médio", "—", "Por aluno com mensalidade", icon_name="tag")
        self.due_card = MetricCard("Vencimentos na semana", "0", "Próximos 7 dias", icon_name="clock")
        for column, card in enumerate((self.active_card, self.revenue_card, self.ticket_card, self.due_card)):
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

        agenda, agenda_layout = panel("softPanel", (22, 20, 22, 20), 10)
        agenda_top = QHBoxLayout()
        agenda_top.setSpacing(12)
        agenda_top.addWidget(icon_label("calendar", theme.GOLD, 18))
        agenda_top.addWidget(label("Agenda do dia", "sectionTitle"))
        agenda_top.addWidget(pill("Próxima etapa", "gold"))
        agenda_top.addStretch()
        capacity = label("2 personais  ·  até 2 alunos por horário", "caption", wrap=False)
        agenda_top.addWidget(capacity)
        agenda_layout.addLayout(agenda_top)
        agenda_layout.addWidget(label("Os horários do dia aparecerão aqui, com os dois personais lado a lado e o bloqueio automático quando o horário lotar."))
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
        self.revenue_card.set_value(brl(summary.monthly_revenue_cents))
        self.ticket_card.set_value(brl(summary.average_fee_cents) if summary.average_fee_cents else "—")
        self.due_card.set_value(str(summary.due_this_week))

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
