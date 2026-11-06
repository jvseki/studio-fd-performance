"""Janela principal: menu lateral animado, páginas com transição e busca rápida.

Recebe os serviços já prontos (composition root em app.py) e distribui para
cada tela. As telas não se conhecem: conversam por sinais ligados aqui.
"""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPainterPath, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from studio_fd import __version__
from studio_fd.services.agenda_service import AgendaService
from studio_fd.services.backup_service import BackupService
from studio_fd.services.cash_service import CashService
from studio_fd.services.contract_service import ContractService
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.finance_service import FinanceService
from studio_fd.services.plan_service import PlanService
from studio_fd.services.report_service import ReportService
from studio_fd.services.settings_service import SettingsService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.paths import AppPaths, resource_root
from studio_fd.views import theme
from studio_fd.views.agenda import AgendaView
from studio_fd.views.backup import BackupView
from studio_fd.views.cash import CashView
from studio_fd.views.contracts import ContractsView
from studio_fd.views.dashboard import DashboardView
from studio_fd.views.finance import FinanceView
from studio_fd.views.plans import PlansView
from studio_fd.views.reports import ReportsView
from studio_fd.views.settings import SettingsView
from studio_fd.views.students import StudentsView
from studio_fd.widgets.icons import icon, pixmap
from studio_fd.widgets.motion import FadeStack, HoverMixin, mix, smooth
from studio_fd.widgets.palette import CommandPalette
from studio_fd.widgets.visuals import label


MODULES = [
    ("Dashboard", "Resumo do dia"),
    ("Agenda", "Horários dos personais"),
    ("Alunos", "Cadastro e fichas"),
    ("Planos", "Frequência e valores"),
    ("Financeiro", "Mensalidades"),
    ("Caixa", "Entradas e saídas"),
    ("Contratos", "PDFs dos alunos"),
    ("Relatórios", "Resultados do mês"),
    ("Backup", "Exportar e restaurar"),
    ("Configurações", "Personais e horários"),
]
ICONS = ["dashboard", "calendar", "users", "layers", "wallet", "cash", "file", "chart", "database", "sliders"]
SECTIONS = {0: "OPERAÇÃO", 4: "FINANCEIRO", 7: "SISTEMA"}
EXPANDED, COLLAPSED = 236, 76


class NavButton(HoverMixin, QPushButton):
    """Item do menu: o fundo do item ativo é desenhado pelo NavIndicator,
    que desliza entre os itens; aqui ficam ícone, texto e hover."""

    def __init__(self, text: str, icon_name: str, shortcut: int):
        super().__init__(text)
        self.icon_name = icon_name
        self.setObjectName("navButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip(f"{text}  (Ctrl+{shortcut})" if shortcut < 10 else text)
        self._setup_hover()

    def sizeHint(self) -> QSize:
        return QSize(190, 40)

    def minimumSizeHint(self) -> QSize:
        return QSize(40, 40)  # permite recolher o menu até ficar só com os ícones

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        compact = self.width() < 120
        if not self.isChecked() and self._hover > 0:
            path = QPainterPath()
            path.addRoundedRect(rect.adjusted(.5, .5, -.5, -.5), 10, 10)
            painter.fillPath(path, mix("#00141417", "#16161A", self._hover))
        if self.hasFocus():
            painter.setPen(QColor(theme.GOLD_LINE))
            painter.drawRoundedRect(rect.adjusted(.5, .5, -.5, -.5), 10, 10)
        color = theme.GOLD if self.isChecked() else mix(theme.TEXT_3, theme.TEXT_2, self._hover).name()
        x = (rect.width() - 18) / 2 if compact else 15 + 2 * self._hover
        painter.drawPixmap(int(x), int(rect.height() / 2 - 9), pixmap(self.icon_name, color, 18))
        if compact:
            return
        font = QFont("Segoe UI")
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.DemiBold if self.isChecked() else QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor(theme.TEXT) if self.isChecked() else mix(theme.TEXT_2, theme.TEXT, self._hover))
        painter.drawText(QRectF(46 + 2 * self._hover, 0, rect.width() - 56, rect.height()), Qt.AlignmentFlag.AlignVCenter, self.text())


class NavIndicator(QWidget):
    """Fundo do item ativo com barra dourada; anima até o item clicado."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.animation = QPropertyAnimation(self, b"geometry", self)
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def go(self, target: QRect, animate: bool = True) -> None:
        self.show()
        self.lower()
        if not animate or self.geometry().isEmpty():
            self.animation.stop()
            self.setGeometry(target)
            return
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(target)
        self.animation.start()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(theme.RAISED))
        painter.setPen(QColor("#2A2721"))
        painter.drawPath(path)
        bar = QPainterPath()
        bar.addRoundedRect(QRectF(0, 11, 3, rect.height() - 22), 1.5, 1.5)
        painter.fillPath(bar, QColor(theme.GOLD))


class Sidebar(QWidget):
    def __init__(self, owner: "MainWindow"):
        super().__init__()
        self.owner = owner
        self.setObjectName("sidebar")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, lambda: self.owner.sync_indicator(False))


class MainWindow(QMainWindow):
    def __init__(self, service: DashboardService, paths: AppPaths, students: StudentService, plans: PlanService):
        super().__init__()
        self.setWindowTitle("Studio FD Performance")
        self.setWindowIcon(QIcon(str(resource_root() / "assets" / "app.ico")))
        self.resize(1360, 880)
        self.setMinimumSize(1050, 680)
        self.restart_requested = False
        sessions = service.sessions
        self.paths = paths
        self.student_service = students
        self.agenda_service = AgendaService(sessions)
        self.finance_service = FinanceService(sessions)
        self.cash_service = CashService(sessions)
        self.contract_service = ContractService(sessions, paths)
        self.settings_service = SettingsService(sessions)
        self.backup_service = BackupService(paths, __version__)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)
        self.toast_host = central

        self.sidebar = Sidebar(self)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(14, 20, 14, 16)
        side.setSpacing(2)
        self.indicator = NavIndicator(self.sidebar)

        brand = QHBoxLayout()
        brand.setContentsMargins(4, 0, 0, 0)
        brand.setSpacing(12)
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo = QPixmap(str(resource_root() / "assets" / "logo.png"))
        if not logo.isNull():
            self.logo_label.setPixmap(logo.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.setWindowIcon(QIcon(logo))
        else:
            self.logo_label.setText("FD")
            self.logo_label.setObjectName("brandMonogram")
        self.logo_label.setFixedSize(40, 40)
        brand.addWidget(self.logo_label)
        self.brand_names = QWidget()
        names = QVBoxLayout(self.brand_names)
        names.setContentsMargins(0, 0, 0, 0)
        names.setSpacing(0)
        names.addWidget(label("Studio FD", "brandName", wrap=False))
        names.addWidget(label("PERFORMANCE", "brandTagline", wrap=False))
        brand.addWidget(self.brand_names, 1)
        self.toggle = QPushButton()
        self.toggle.setObjectName("sidebarToggle")
        self.toggle.setIcon(icon("sidebar", theme.TEXT_3, 18))
        self.toggle.setFixedSize(30, 30)
        self.toggle.setToolTip("Recolher ou expandir o menu")
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.clicked.connect(self.toggle_sidebar)
        brand.addWidget(self.toggle)
        side.addLayout(brand)
        side.addSpacing(18)

        self.search_hint = QPushButton("  Buscar...                Ctrl+K")
        self.search_hint.setObjectName("paletteHint")
        self.search_hint.setIcon(icon("search", theme.TEXT_3, 15))
        self.search_hint.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_hint.clicked.connect(self.open_palette)
        self.search_hint.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search_hint.setMinimumWidth(40)
        side.addWidget(self.search_hint)
        side.addSpacing(12)

        self.pages = FadeStack()
        self.navigation = QButtonGroup(self)
        self.navigation.setExclusive(True)
        self.dashboard = DashboardView(service)
        self.agenda = AgendaView(self.agenda_service, students)
        self.students = StudentsView(students, plans)
        self.students.extras = self
        self.plans = PlansView(plans)
        self.finance = FinanceView(self.finance_service, students)
        self.cash = CashView(self.cash_service)
        self.contracts = ContractsView(self.contract_service, students)
        self.reports = ReportsView(ReportService(sessions))
        self.backup = BackupView(self.backup_service)
        self.settings = SettingsView(self.settings_service, paths)
        self.views = [self.dashboard, self.agenda, self.students, self.plans, self.finance, self.cash,
                      self.contracts, self.reports, self.backup, self.settings]

        for view in (self.agenda, self.finance, self.contracts):
            view.open_student.connect(self.open_student)
        for view in (self.students, self.plans, self.agenda, self.finance, self.cash, self.contracts, self.settings):
            view.changed.connect(self.dashboard.refresh)
        self.students.changed.connect(self.plans.refresh)
        self.plans.changed.connect(self.students.refresh)
        self.settings.changed.connect(self.agenda.refresh)
        self.backup.restart_requested.connect(self.request_restart)
        self.dashboard.open_students.connect(lambda: self.go(2))
        if hasattr(self.dashboard, "open_page"):
            self.dashboard.open_page.connect(self.go)

        self.section_labels = []
        for index, (title, _detail) in enumerate(MODULES):
            if index in SECTIONS:
                if index:
                    side.addSpacing(14)
                section = label(SECTIONS[index], "navSection", wrap=False)
                self.section_labels.append(section)
                side.addWidget(section)
                side.addSpacing(6)
            button = NavButton(title, ICONS[index], index + 1)
            self.navigation.addButton(button, index)
            side.addWidget(button)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(self.views[index])
            smooth(scroll)
            self.pages.addWidget(scroll)
        self.navigation.button(0).setChecked(True)
        self.navigation.idClicked.connect(self.navigate)
        side.addStretch()

        self.footer = QFrame()
        self.footer.setObjectName("sidebarFooter")
        footer_layout = QVBoxLayout(self.footer)
        footer_layout.setContentsMargins(14, 12, 14, 12)
        footer_layout.setSpacing(2)
        status = QHBoxLayout()
        status.setSpacing(7)
        dot = QLabel()
        dot.setFixedSize(7, 7)
        dot.setStyleSheet(f"background: {theme.SUCCESS}; border-radius: 3px;")
        status.addWidget(dot)
        status.addWidget(label("Dados neste computador", "muted", wrap=False), 1)
        footer_layout.addLayout(status)
        footer_layout.addWidget(label(f"Andradina · SP   ·   v{__version__}", "caption", wrap=False))
        self.footer.setToolTip(str(paths.root))
        side.addWidget(self.footer)

        self.side_scroll = QScrollArea()
        self.side_scroll.setObjectName("sidebarScroll")
        self.side_scroll.setFixedWidth(EXPANDED)
        self.side_scroll.setWidgetResizable(True)
        self.side_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.side_scroll.setWidget(self.sidebar)
        root.addWidget(self.side_scroll)
        root.addWidget(self.pages, 1)
        self.statusBar().hide()
        self.statusBar().messageChanged.connect(lambda text: self.statusBar().setVisible(bool(text)))

        self.width_animation = QVariantAnimation(self)
        self.width_animation.setDuration(280)
        self.width_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.width_animation.valueChanged.connect(lambda value: self.side_scroll.setFixedWidth(int(value)))
        self.width_animation.finished.connect(lambda: self.sync_indicator(False))

        QShortcut(QKeySequence("Ctrl+K"), self, activated=self.open_palette)
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self.toggle_sidebar)
        for index in range(9):
            QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self, activated=lambda i=index: self.go(i))

    # Navegação ---------------------------------------------------------
    def go(self, index: int) -> None:
        self.navigation.button(index).click()

    def navigate(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.sync_indicator(True)
        view = self.views[index]
        if hasattr(view, "refresh"):
            view.refresh()

    def sync_indicator(self, animate: bool = True) -> None:
        button = self.navigation.checkedButton()
        if button is not None and button.isVisible():
            self.indicator.go(button.geometry(), animate)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, lambda: self.sync_indicator(False))

    def toggle_sidebar(self) -> None:
        compact = self.side_scroll.width() > (EXPANDED + COLLAPSED) / 2
        for widget in (self.logo_label, self.brand_names, self.footer, *self.section_labels):
            widget.setVisible(not compact)
        self.search_hint.setText("" if compact else "  Buscar...                Ctrl+K")
        self.width_animation.stop()
        self.width_animation.setStartValue(self.side_scroll.width())
        self.width_animation.setEndValue(COLLAPSED if compact else EXPANDED)
        self.width_animation.start()

    # Ações entre telas ---------------------------------------------------
    def open_student(self, student_id: int) -> None:
        self.students.open_profile(student_id)
        self.navigate(self.pages.currentIndex())

    def request_restart(self) -> None:
        self.restart_requested = True
        self.close()

    def open_palette(self) -> None:
        entries = [(title, f"Ir para · {detail}", ICONS[index], lambda i=index: self.go(i)) for index, (title, detail) in enumerate(MODULES)]
        entries += [
            ("Novo aluno", "Cadastrar", "plus", lambda: (self.go(2), self.students.create())),
            ("Agendar atendimento", "Agenda", "calendar", lambda: (self.go(1), self.agenda.book())),
            ("Gerar mensalidades do mês", "Financeiro", "repeat", lambda: (self.go(4), self.finance.generate())),
            ("Lançar saída no caixa", "Caixa", "arrow-up", lambda: (self.go(5), self.cash.add("saida"))),
            ("Exportar backup completo", "Backup", "download", lambda: (self.go(8), self.backup.export())),
        ]
        try:
            people = self.student_service.list()
        except Exception:
            people = []
        entries += [(person.full_name, "Abrir ficha" + ("" if person.active else " · inativo"), "user",
                     lambda sid=person.id: self.open_student(sid)) for person in people]
        CommandPalette(entries, self).exec()
