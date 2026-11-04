import logging

from PySide6.QtCore import QDate, QLocale, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QGridLayout, QHeaderView, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QVBoxLayout, QWidget,
)

from studio_fd.services.dashboard_service import DashboardService
from studio_fd.widgets.metric_card import MetricCard


def label(text: str, role: str = "muted") -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(role)
    widget.setWordWrap(True)
    return widget


class DashboardView(QWidget):
    open_students = Signal()

    def __init__(self, service: DashboardService):
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(22)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(6)
        titles.addWidget(label("VISÃO GERAL DO STUDIO", "eyebrow"))
        titles.addWidget(label("Dashboard", "title"))
        self.date_label = label("")
        titles.addWidget(self.date_label)
        header.addLayout(titles, 1)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setAccessibleName("Atualizar indicadores do Dashboard")
        self.refresh_button.clicked.connect(self.refresh)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        welcome = QFrame()
        welcome.setObjectName("welcomePanel")
        welcome_layout = QHBoxLayout(welcome)
        welcome_layout.setContentsMargins(20, 17, 20, 17)
        welcome_text = QVBoxLayout()
        welcome_text.addWidget(label("Cada aluno, um acompanhamento de perto.", "sectionTitle"))
        welcome_text.addWidget(label("Cadastre seus alunos, organize os planos e mantenha o contato por perto."))
        welcome_layout.addLayout(welcome_text, 1)
        students_button = QPushButton("Ver alunos")
        students_button.clicked.connect(self.open_students.emit)
        welcome_layout.addWidget(students_button)
        layout.addWidget(welcome)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.active_card = MetricCard("Alunos ativos", "0", "Cadastros no banco local", accent=True)
        cards = [
            self.active_card,
            MetricCard("Agendados hoje", "—", "Disponível na etapa de agenda"),
            MetricCard("Horários ocupados", "—", "Disponível na etapa de agenda"),
            MetricCard("Horários disponíveis", "—", "Definir expediente e intervalos"),
            MetricCard("A vencer", "—", "Disponível na etapa financeira"),
            MetricCard("Mensalidades atrasadas", "—", "Disponível na etapa financeira"),
            MetricCard("Recebido no mês", "—", "Disponível na etapa financeira", accent=True),
        ]
        for index, card in enumerate(cards):
            row, column = divmod(index, 4)
            grid.addWidget(card, row, column, 1, 2 if index == 6 else 1)
        for column in range(4):
            grid.setColumnStretch(column, 1)
        layout.addLayout(grid)

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 18, 20, 18)
        panel_layout.setSpacing(14)
        agenda_header = QHBoxLayout()
        agenda_header.addWidget(label("Agenda do dia", "sectionTitle"))
        agenda_header.addStretch()
        capacity = label("2 personais  ·  Até 2 alunos por horário", "caption")
        capacity.setWordWrap(False)
        agenda_header.addWidget(capacity)
        panel_layout.addLayout(agenda_header)
        self.schedule = QTableWidget(0, 3)
        self.schedule.setHorizontalHeaderLabels(["HORÁRIO", "PERSONAL 1", "PERSONAL 2"])
        self.schedule.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.schedule.verticalHeader().hide()
        self.schedule.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.schedule.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.schedule.setFixedHeight(42)
        panel_layout.addWidget(self.schedule)
        empty = label("A agenda será configurada em uma próxima etapa.")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(empty)
        note = label("Os horários de funcionamento e a duração dos atendimentos ainda não foram definidos.", "caption")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(note)
        layout.addWidget(panel)

        self.feedback = label("", "caption")
        layout.addWidget(self.feedback)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        locale = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
        self.date_label.setText(locale.toString(QDate.currentDate(), "dddd, d 'de' MMMM 'de' yyyy"))
        try:
            summary = self.service.summary()
        except Exception:
            logging.getLogger(__name__).exception("Falha ao atualizar o Dashboard")
            self.active_card.set_value("—")
            self.feedback.setText("Não foi possível consultar os dados. Tente atualizar novamente; detalhes no log local.")
            return
        self.active_card.set_value(str(summary.active_students))
        self.feedback.setText("Dados locais  •  Indicadores com — aguardam a implementação dos próximos módulos.")
