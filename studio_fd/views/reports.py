"""Relatórios: receita e despesas dos últimos meses, frequência e distribuição."""

import logging

from PySide6.QtCore import QEasingCurve, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QWidget

from studio_fd.services.report_service import MonthFlow, ReportService
from studio_fd.utils.dates import short_month
from studio_fd.utils.formatting import brl
from studio_fd.views import theme
from studio_fd.views.dashboard import PlanBars
from studio_fd.widgets.controls import DateNavigator, font
from studio_fd.widgets.metric_card import MetricCard
from studio_fd.widgets.visuals import label, page_header, page_layout, panel


class FlowChart(QWidget):
    """Barras de entradas (dourado) e saídas (cinza) por mês; crescem ao aparecer."""

    def __init__(self):
        super().__init__()
        self.flows: list[MonthFlow] = []
        self.progress = 1.0
        self.hovered = -1
        self.setMinimumHeight(260)
        self.setMouseTracking(True)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(700)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._grow)

    def _grow(self, value) -> None:
        self.progress = float(value)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(600, 260)

    def set_flows(self, flows: list[MonthFlow]) -> None:
        self.flows = flows
        self.animation.stop()
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def _group(self, index: int) -> QRectF:
        width = self.width() / max(1, len(self.flows))
        return QRectF(index * width, 0, width, self.height())

    def mouseMoveEvent(self, event) -> None:
        index = next((i for i in range(len(self.flows)) if self._group(i).contains(event.position())), -1)
        if index != self.hovered:
            self.hovered = index
            self.update()

    def leaveEvent(self, event) -> None:
        self.hovered = -1
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        top = max([1] + [max(flow.income_cents, flow.expense_cents) for flow in self.flows])
        chart_top, chart_bottom = 34, self.height() - 30
        height = chart_bottom - chart_top
        painter.setPen(QColor(theme.BORDER))
        for step in range(4):
            y = chart_top + height * step / 3
            painter.drawLine(0, int(y), self.width(), int(y))
        for index, flow in enumerate(self.flows):
            group = self._group(index)
            if index == self.hovered:
                highlight = QPainterPath()
                highlight.addRoundedRect(group.adjusted(6, 0, -6, 0), 10, 10)
                painter.fillPath(highlight, QColor(theme.RAISED))
            bar = min(28, group.width() * .22)
            center = group.center().x()
            for offset, value, color in ((-bar - 3, flow.income_cents, theme.GOLD), (3, flow.expense_cents, "#5A5852")):
                h = max(2, height * value / top * self.progress) if value else 2
                path = QPainterPath()
                path.addRoundedRect(QRectF(center + offset, chart_bottom - h, bar, h), 4, 4)
                painter.fillPath(path, QColor(color))
            painter.setFont(font(11, QFont.Weight.DemiBold if index == len(self.flows) - 1 else QFont.Weight.Normal))
            painter.setPen(QColor(theme.TEXT if index == len(self.flows) - 1 else theme.TEXT_3))
            painter.drawText(QRectF(group.left(), chart_bottom + 8, group.width(), 18), Qt.AlignmentFlag.AlignCenter,
                             f"{short_month(flow.month)}/{flow.month.year % 100:02d}")
            if index == self.hovered:
                painter.setFont(font(11, QFont.Weight.DemiBold))
                painter.setPen(QColor(theme.GOLD))
                painter.drawText(QRectF(group.left(), 0, group.width(), 16), Qt.AlignmentFlag.AlignCenter, f"+ {brl(flow.income_cents)}")
                painter.setPen(QColor(theme.TEXT_2))
                painter.drawText(QRectF(group.left(), 16, group.width(), 16), Qt.AlignmentFlag.AlignCenter, f"− {brl(flow.expense_cents)}")


class ReportsView(QWidget):
    def __init__(self, service: ReportService):
        super().__init__()
        self.service = service
        layout = page_layout(self)
        self.navigator = DateNavigator("month")
        self.navigator.changed.connect(lambda _m: self.refresh())
        layout.addLayout(page_header("SISTEMA", "Relatórios", label("Resultados do mês com base no Caixa e na Agenda."), [self.navigator]))
        grid = QGridLayout()
        grid.setSpacing(14)
        self.income = MetricCard("Entradas no mês", "R$ 0,00", "", accent=True, icon_name="arrow-down")
        self.expense = MetricCard("Saídas no mês", "R$ 0,00", "", icon_name="arrow-up")
        self.result = MetricCard("Resultado", "R$ 0,00", "", icon_name="trend")
        self.attendance = MetricCard("Presença", "—", "", icon_name="calendar")
        for column, card in enumerate((self.income, self.expense, self.result, self.attendance)):
            grid.addWidget(card, 0, column)
            grid.setColumnStretch(column, 1)
        layout.addLayout(grid)

        chart_panel, chart_layout = panel(margins=(22, 18, 22, 16))
        top = QHBoxLayout()
        top.addWidget(label("Entradas e saídas · últimos 6 meses", "sectionTitle"), 1)
        legend = label(f"<span style='color:{theme.GOLD}'>●</span>&nbsp; Entradas &nbsp;&nbsp;&nbsp; <span style='color:#5A5852'>●</span>&nbsp; Saídas", "caption", wrap=False)
        legend.setTextFormat(Qt.TextFormat.RichText)
        top.addWidget(legend)
        chart_layout.addLayout(top)
        self.chart = FlowChart()
        chart_layout.addWidget(self.chart)
        layout.addWidget(chart_panel)

        row = QHBoxLayout()
        row.setSpacing(14)
        plans, plans_layout = panel()
        plans_layout.addWidget(label("Alunos ativos por plano", "sectionTitle"))
        self.plan_bars = PlanBars()
        plans_layout.addWidget(self.plan_bars)
        plans_layout.addStretch()
        expenses, expenses_layout = panel()
        expenses_layout.addWidget(label("Despesas por categoria", "sectionTitle"))
        self.categories = PlanBars(brl)
        expenses_layout.addWidget(self.categories)
        self.categories_empty = label("Nenhuma saída no mês.", "caption")
        expenses_layout.addWidget(self.categories_empty)
        expenses_layout.addStretch()
        frequent, frequent_layout = panel()
        frequent_layout.addWidget(label("Mais frequentes no mês", "sectionTitle"))
        self.frequent = PlanBars()
        frequent_layout.addWidget(self.frequent)
        self.frequent_empty = label("Marque atendimentos como concluídos na Agenda.", "caption")
        frequent_layout.addWidget(self.frequent_empty)
        frequent_layout.addStretch()
        for widget in (plans, expenses, frequent):
            row.addWidget(widget, 1)
        layout.addLayout(row)
        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        try:
            report = self.service.build(self.navigator.value)
        except Exception:
            logging.getLogger(__name__).exception("Falha ao montar relatório")
            self.feedback.setText("Não foi possível montar o relatório.")
            return
        current = report.current
        self.income.set_value(brl(current.income_cents), "Mensalidades e outras entradas")
        self.expense.set_value(brl(current.expense_cents), f"{len(report.expenses_by_category)} categoria(s)")
        balance = current.income_cents - current.expense_cents
        self.result.set_value(("− " if balance < 0 else "") + brl(abs(balance)), "Entradas menos saídas")
        done, missed = report.attendance.get("concluido", 0), report.attendance.get("falta", 0)
        total = done + missed
        self.attendance.set_value(f"{round(done * 100 / total)}%" if total else "—",
                                  f"{done} concluído(s) · {missed} falta(s)")
        self.chart.set_flows(report.flows)
        self.plan_bars.set_rows(report.by_plan)
        self.categories.set_rows(report.expenses_by_category)
        self.categories.setVisible(bool(report.expenses_by_category))
        self.categories_empty.setVisible(not report.expenses_by_category)
        self.frequent.set_rows(report.top_students)
        self.frequent.setVisible(bool(report.top_students))
        self.frequent_empty.setVisible(not report.top_students)
        self.feedback.setText(f"{report.active_students} aluno(s) ativo(s)  ·  {report.new_students} novo(s) cadastro(s) no mês")
