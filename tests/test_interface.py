import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontDatabase, QPixmap
from PySide6.QtWidgets import QApplication

from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.models import Student
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.paths import AppPaths
from studio_fd.views.main_window import MainWindow, MODULES
from studio_fd.views.theme import STYLESHEET


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        for filename in ("segoeui.ttf", "segoeuib.ttf", "georgia.ttf"):
            QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / filename))
        cls.app.setStyle("Fusion")
        cls.app.setStyleSheet(STYLESHEET)

    def test_navigation_refresh_logo_and_small_window(self):
        with TemporaryDirectory() as directory:
            paths = AppPaths(Path(directory))
            paths.ensure_directories()
            engine = create_database_engine(paths.database)
            window = None
            try:
                migrate_database(engine)
                sessions = create_session_factory(engine)
                service = DashboardService(sessions)
                with patch("studio_fd.views.main_window.resource_root", return_value=Path(directory)):
                    window = MainWindow(service, paths, StudentService(sessions), PlanService(sessions))
                window.show()
                self.app.processEvents()
                self.assertEqual(window.logo_label.text(), "FD")
                self.assertEqual(window.dashboard.active_card.value_label.text(), "0")
                for index in range(len(MODULES)):
                    window.navigation.button(index).click()
                    self.assertEqual(window.pages.currentIndex(), index)
                with sessions.begin() as session:
                    session.add(Student(full_name="Teste de interface", phone=""))
                window.navigation.button(0).click()
                self.assertEqual(window.dashboard.active_card.value_label.text(), "1")
                window.resize(1050, 680)
                self.app.processEvents()
                self.assertLessEqual(window.pages.currentWidget().widget().minimumSizeHint().width(), window.pages.width())
                window.close()
                assets = Path(directory) / "assets"
                assets.mkdir()
                pixmap = QPixmap(100, 80)
                pixmap.fill()
                pixmap.save(str(assets / "logo.png"))
                with patch("studio_fd.views.main_window.resource_root", return_value=Path(directory)):
                    window = MainWindow(service, paths, StudentService(sessions), PlanService(sessions))
                self.assertFalse(window.logo_label.pixmap().isNull())
            finally:
                if window is not None:
                    window.close()
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
