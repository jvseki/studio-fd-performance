"""Captura a interface com banco temporário; não altera os dados do Studio."""

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.services.records import PlanInput, StudentInput
from studio_fd.utils.paths import AppPaths, resource_root
from studio_fd.views.main_window import MainWindow
from studio_fd.views.theme import STYLESHEET
from studio_fd.views.student_form import StudentDialog
from studio_fd.views.student_profile import StudentProfile


def main() -> None:
    app = QApplication([])
    # O plugin offscreen não descobre automaticamente as fontes do Windows.
    for filename in ("segoeui.ttf", "segoeuib.ttf", "georgia.ttf"):
        QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / filename))
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    with TemporaryDirectory() as directory:
        paths = AppPaths(Path(directory))
        paths.ensure_directories()
        engine = create_database_engine(paths.database)
        try:
            migrate_database(engine)
            sessions = create_session_factory(engine)
            window = MainWindow(DashboardService(sessions), paths, StudentService(sessions), PlanService(sessions))
            window.show()
            app.processEvents()
            destination = resource_root() / "docs" / "dashboard-etapa-2.png"
            if not window.grab().save(str(destination)):
                raise RuntimeError("Não foi possível salvar a captura.")
            print(destination)
            plans = PlanService(sessions)
            students = StudentService(sessions)
            plan = plans.save(PlanInput("3 vezes por semana · demonstração", 3, 45000, 1))
            student = students.save(StudentInput("João · demonstração", "18999999999", plan_id=plan.id, monthly_fee_cents=45000, due_day=10))
            students.save(StudentInput("Ana · demonstração", "18988888888"))
            window.navigation.button(2).click()
            app.processEvents()
            window.grab().save(str(resource_root() / "docs" / "alunos-etapa-2.png"))
            for name, dialog in (
                ("cadastro-etapa-2.png", StudentDialog(students, plans)),
                ("ficha-etapa-2.png", StudentProfile(student.id, students, plans)),
            ):
                dialog.show()
                app.processEvents()
                dialog.grab().save(str(resource_root() / "docs" / name))
                dialog.close()
            window.close()
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
