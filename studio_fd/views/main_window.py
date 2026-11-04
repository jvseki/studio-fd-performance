from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from studio_fd import __version__
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.paths import AppPaths, resource_root
from studio_fd.views.dashboard import DashboardView, label
from studio_fd.views.placeholder import PlaceholderView
from studio_fd.views.plans import PlansView
from studio_fd.views.students import StudentsView


MODULES = [
    ("Dashboard", ""),
    ("Agenda", "Agenda diária com dois personais e validação do limite de dois alunos por horário."),
    ("Alunos", "Próxima etapa: cadastro, pesquisa por nome, gaveta alfabética e ficha individual do aluno."),
    ("Planos", "Criação e edição dos planos, valores, duração e quantidade de treinos por semana."),
    ("Financeiro", "Mensalidades por aluno, vencimentos e registro de pagamentos."),
    ("Caixa", "Entradas, saídas, saldo e histórico de movimentações do Studio."),
    ("Contratos", "Anexos em PDF guardados na pasta de contratos, com abertura no programa padrão do Windows."),
    ("Relatórios", "Consultas da operação e dos resultados do Studio."),
    ("Backup", "Ao abrir uma versão nova com dados existentes, o sistema cria uma cópia na pasta backups antes de preparar o banco. A tela de exportação, a restauração e os backups periódicos serão implementados em outra etapa."),
    ("Configurações", "Configuração dos personais, expediente e preferências do Studio."),
]


class MainWindow(QMainWindow):
    def __init__(self, service: DashboardService, paths: AppPaths, students: StudentService, plans: PlanService):
        super().__init__()
        self.setWindowTitle("Studio FD Performance")
        self.setWindowIcon(QIcon(str(resource_root() / "assets" / "app.ico")))
        self.resize(1320, 900)
        self.setMinimumSize(1050, 680)
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 26, 16, 18)
        side.setSpacing(5)
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(resource_root() / "assets" / "logo.png"))
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(154, 154, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.setWindowIcon(QIcon(pixmap))
        else:
            self.logo_label.setText("FD")
            self.logo_label.setObjectName("brandMonogram")
        side.addWidget(self.logo_label)
        for text, role in [("PERFORMANCE", "brandTitle"), ("S T U D I O", "brandSubtitle")]:
            brand = label(text, role)
            brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
            side.addWidget(brand)
        side.addSpacing(26)
        side.addWidget(label("   GESTÃO DO STUDIO", "caption"))
        side.addSpacing(8)

        self.pages = QStackedWidget()
        self.navigation = QButtonGroup(self)
        self.navigation.setExclusive(True)
        self.dashboard = DashboardView(service)
        self.students = StudentsView(students, plans)
        self.plans = PlansView(plans)
        self.students.changed.connect(self.dashboard.refresh)
        self.students.changed.connect(self.plans.refresh)
        self.plans.changed.connect(self.students.refresh)
        active_pages = {0: self.dashboard, 2: self.students, 3: self.plans}
        for index, (title, description) in enumerate(MODULES):
            button = QPushButton(title)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.navigation.addButton(button, index)
            side.addWidget(button)
            page = active_pages[index] if index in active_pages else PlaceholderView(title, description)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.pages.addWidget(scroll)
        self.navigation.button(0).setChecked(True)
        self.navigation.idClicked.connect(self.navigate)
        self.dashboard.open_students.connect(lambda: self.navigation.button(2).click())
        side.addStretch()
        side.addWidget(label("Aplicativo local", "badge"))
        side.addSpacing(6)
        side.addWidget(label(f"Andradina · SP    /    v{__version__}", "caption"))

        side_scroll = QScrollArea()
        side_scroll.setFixedWidth(222)
        side_scroll.setWidgetResizable(True)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        side_scroll.setWidget(sidebar)
        root.addWidget(side_scroll)
        root.addWidget(self.pages, 1)
        self.statusBar().showMessage("Dados salvos neste computador")
        location = label("Dados do aplicativo", "caption")
        location.setToolTip(str(paths.root))
        self.statusBar().addPermanentWidget(location)

    def navigate(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        if index == 0:
            self.dashboard.refresh()
        elif index == 2:
            self.students.refresh()
        elif index == 3:
            self.plans.refresh()
