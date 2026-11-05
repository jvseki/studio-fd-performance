from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from studio_fd import __version__
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.paths import AppPaths, resource_root
from studio_fd.views import theme
from studio_fd.views.dashboard import DashboardView
from studio_fd.views.placeholder import PlaceholderView
from studio_fd.views.plans import PlansView
from studio_fd.views.students import StudentsView
from studio_fd.widgets.icons import pixmap
from studio_fd.widgets.visuals import label


MODULES = [
    ("Dashboard", ""),
    ("Agenda", "Agenda diária com os dois personais lado a lado e bloqueio automático quando o horário atingir o limite de dois alunos."),
    ("Alunos", ""),
    ("Planos", ""),
    ("Financeiro", "Mensalidades de cada aluno com vencimento, registro de pagamento e indicação de atrasos."),
    ("Caixa", "Entradas, saídas e saldo do dia, com histórico simples de movimentações do Studio."),
    ("Contratos", "PDF do contrato anexado à ficha do aluno e aberto no programa padrão do Windows."),
    ("Relatórios", "Consultas da operação: alunos por plano, receita do mês e frequência de atendimento."),
    ("Backup", "Exportar e restaurar um arquivo único com todos os dados. Hoje o sistema já cria uma cópia automática antes de cada atualização."),
    ("Configurações", "Cadastro dos personais, horário de funcionamento e preferências do Studio."),
]
ICONS = ["dashboard", "calendar", "users", "layers", "wallet", "cash", "file", "chart", "database", "sliders"]
SECTIONS = {0: "OPERAÇÃO", 4: "FINANCEIRO", 7: "SISTEMA"}
READY = {0, 2, 3}


class NavButton(QPushButton):
    """Item do menu pintado à mão: ícone, texto e marca discreta de 'em breve'."""

    def __init__(self, text: str, icon_name: str, ready: bool):
        super().__init__(text)
        self.icon_name = icon_name
        self.ready = ready
        self.setObjectName("navButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setFixedHeight(38)
        if not ready:
            self.setToolTip("Em desenvolvimento")

    def sizeHint(self) -> QSize:
        return QSize(190, 38)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        hovered = self.underMouse()
        if self.isChecked() or hovered:
            path = QPainterPath()
            path.addRoundedRect(rect.adjusted(.5, .5, -.5, -.5), 8, 8)
            painter.fillPath(path, QColor(theme.RAISED if self.isChecked() else "#141417"))
        if self.isChecked():
            bar = QPainterPath()
            bar.addRoundedRect(QRectF(0, 10, 3, rect.height() - 20), 1.5, 1.5)
            painter.fillPath(bar, QColor(theme.GOLD))
        if self.hasFocus() and not self.isChecked():
            painter.setPen(QColor(theme.GOLD_LINE))
            painter.drawRoundedRect(rect.adjusted(.5, .5, -.5, -.5), 8, 8)
        icon_color = theme.GOLD if self.isChecked() else (theme.TEXT_2 if hovered else theme.TEXT_3)
        painter.drawPixmap(14, int(rect.height() / 2 - 9), pixmap(self.icon_name, icon_color, 18))
        font = QFont("Segoe UI")
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.DemiBold if self.isChecked() else QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor(theme.TEXT if self.isChecked() or hovered else theme.TEXT_2))
        painter.drawText(QRectF(44, 0, rect.width() - 90, rect.height()), Qt.AlignmentFlag.AlignVCenter, self.text())
        if not self.ready:
            painter.setPen(QColor("#4C4B47"))
            small = QFont("Segoe UI")
            small.setPixelSize(10)
            painter.setFont(small)
            painter.drawText(QRectF(rect.width() - 52, 0, 42, rect.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "em breve")


class MainWindow(QMainWindow):
    def __init__(self, service: DashboardService, paths: AppPaths, students: StudentService, plans: PlanService):
        super().__init__()
        self.setWindowTitle("Studio FD Performance")
        self.setWindowIcon(QIcon(str(resource_root() / "assets" / "app.ico")))
        self.resize(1320, 860)
        self.setMinimumSize(1050, 680)
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 22, 14, 16)
        side.setSpacing(2)

        brand = QHBoxLayout()
        brand.setContentsMargins(6, 0, 0, 0)
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
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("Studio FD", "brandName", wrap=False))
        names.addWidget(label("PERFORMANCE", "brandTagline", wrap=False))
        brand.addLayout(names, 1)
        side.addLayout(brand)
        side.addSpacing(26)

        self.pages = QStackedWidget()
        self.navigation = QButtonGroup(self)
        self.navigation.setExclusive(True)
        self.dashboard = DashboardView(service)
        self.students = StudentsView(students, plans)
        self.plans = PlansView(plans)
        self.students.changed.connect(self.dashboard.refresh)
        self.students.changed.connect(self.plans.refresh)
        self.plans.changed.connect(self.students.refresh)
        self.plans.changed.connect(self.dashboard.refresh)
        active_pages = {0: self.dashboard, 2: self.students, 3: self.plans}
        for index, (title, description) in enumerate(MODULES):
            if index in SECTIONS:
                if index:
                    side.addSpacing(16)
                side.addWidget(label(SECTIONS[index], "navSection", wrap=False))
                side.addSpacing(6)
            button = NavButton(title, ICONS[index], index in READY)
            self.navigation.addButton(button, index)
            side.addWidget(button)
            page = active_pages[index] if index in active_pages else PlaceholderView(title, description, ICONS[index])
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(page)
            self.pages.addWidget(scroll)
        self.navigation.button(0).setChecked(True)
        self.navigation.idClicked.connect(self.navigate)
        self.dashboard.open_students.connect(lambda: self.navigation.button(2).click())
        side.addStretch()

        footer = QFrame()
        footer.setObjectName("sidebarFooter")
        footer_layout = QVBoxLayout(footer)
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
        footer.setToolTip(str(paths.root))
        side.addWidget(footer)

        side_scroll = QScrollArea()
        side_scroll.setObjectName("sidebarScroll")
        side_scroll.setFixedWidth(232)
        side_scroll.setWidgetResizable(True)
        side_scroll.setFrameShape(QFrame.Shape.NoFrame)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        side_scroll.setWidget(sidebar)
        root.addWidget(side_scroll)
        root.addWidget(self.pages, 1)
        self.statusBar().hide()
        self.statusBar().messageChanged.connect(lambda text: self.statusBar().setVisible(bool(text)))

    def navigate(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        if index == 0:
            self.dashboard.refresh()
        elif index == 2:
            self.students.refresh()
        elif index == 3:
            self.plans.refresh()
