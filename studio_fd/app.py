"""Composition root: conecta infraestrutura, serviços e interface."""

import logging
from logging.handlers import RotatingFileHandler
import sys

from PySide6.QtCore import QLocale, QLockFile
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from studio_fd import __version__
from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.plan_service import PlanService
from studio_fd.services.student_service import StudentService
from studio_fd.services.update_service import prepare_update, confirm_version
from studio_fd.utils.paths import AppPaths, resource_root
from studio_fd.utils.windows import identify_windows_app
from studio_fd.views.main_window import MainWindow
from studio_fd.views.theme import STYLESHEET, apply_palette


def run() -> int:
    identify_windows_app()
    app = QApplication(sys.argv)
    app.setApplicationName("Studio FD Performance")
    app.setOrganizationName("StudioFDPerformance")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(resource_root() / "assets" / "app.ico")))
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    apply_palette(app)
    app.setStyleSheet(STYLESHEET)
    QLocale.setDefault(QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil))
    engine = None
    data_lock = None
    try:
        paths = AppPaths.default()
        paths.ensure_directories()
        data_lock = QLockFile(str(paths.root / "studio_fd.lock"))
        data_lock.setStaleLockTime(0)
        if not data_lock.tryLock(0):
            if data_lock.error() != QLockFile.LockError.LockFailedError:
                raise OSError("Não foi possível reservar a pasta de dados para abrir o programa.")
            QMessageBox.information(None, "Studio já está aberto", "Já existe uma janela usando esses dados. Use a janela aberta ou feche-a antes de iniciar outra versão.")
            return 1
        handler = RotatingFileHandler(paths.logs / "studio_fd.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        snapshot = prepare_update(paths, __version__)
        engine = create_database_engine(paths.database)
        migrate_database(engine)
        sessions = create_session_factory(engine)
        service = DashboardService(sessions)
        window = MainWindow(service, paths, StudentService(sessions), PlanService(sessions))
        confirm_version(paths, __version__)
        if snapshot is not None:
            window.statusBar().showMessage("Cópia de segurança criada antes da atualização. Consulte a pasta backups.")
    except Exception as error:
        logging.getLogger(__name__).exception("Falha ao iniciar o aplicativo")
        message = str(error) if isinstance(error, ValueError) else "Não foi possível preparar os dados ou a cópia de segurança da atualização.\nVerifique o espaço em disco, o acesso à pasta de dados e o log studio_fd.log."
        QMessageBox.critical(None, "Não foi possível iniciar", message)
        if engine is not None:
            engine.dispose()
        if data_lock is not None:
            data_lock.unlock()
        return 1
    app.aboutToQuit.connect(engine.dispose)
    app.aboutToQuit.connect(data_lock.unlock)
    window.show()
    return app.exec()
