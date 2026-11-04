from dataclasses import replace
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QDialog

from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.plan_service import PlanService
from studio_fd.services.records import PlanInput, StudentInput
from studio_fd.services.student_service import StudentService
from studio_fd.utils.paths import AppPaths
from studio_fd.views.main_window import MainWindow
from studio_fd.views.plans import PlanDialog
from studio_fd.views.student_form import StudentDialog
from studio_fd.views.student_profile import StudentProfile
from studio_fd.views.theme import STYLESHEET
from studio_fd.views.whatsapp import WhatsAppDialog


class RegistrationUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        for name in ("segoeui.ttf", "segoeuib.ttf", "georgia.ttf"):
            QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name))
        cls.app.setStyle("Fusion")
        cls.app.setStyleSheet(STYLESHEET)

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.paths = AppPaths(Path(self.temp.name))
        self.paths.ensure_directories()
        self.engine = create_database_engine(self.paths.database)
        migrate_database(self.engine)
        self.sessions = create_session_factory(self.engine)
        self.students = StudentService(self.sessions)
        self.plans = PlanService(self.sessions)
        self.windows = []

    def tearDown(self):
        for window in self.windows:
            window.close()
        self.app.processEvents()
        self.engine.dispose()
        self.temp.cleanup()

    def keep(self, widget):
        self.windows.append(widget)
        return widget

    def test_forms_save_edit_and_preserve_optional_fields(self):
        plan_form = self.keep(PlanDialog(self.plans))
        plan_form.name.setText("Personalizado")
        plan_form.price.set_cents(45029)
        plan_form.workouts.setValue(3)
        plan_form.save_button.click()
        self.assertEqual(plan_form.result(), QDialog.DialogCode.Accepted)
        form = self.keep(StudentDialog(self.students, self.plans))
        form.save_button.click()
        self.assertIsNone(form.saved_record)
        self.assertIn("nome", form.feedback.text())
        form.name.setText("João de teste")
        form.phone.setText("(18) 99999-9999")
        form.plan.setCurrentIndex(form.plan.findData(plan_form.saved_record.id))
        form.apply_plan_price()
        self.assertEqual(form.fee.cents(), 45029)
        form.fee.set_cents(42099)
        form.due_day.setValue(10)
        form.cpf.setText("529.982.247-25")
        form.notes.setPlainText("Observação mantida")
        form.save_button.click()
        self.assertEqual(form.result(), QDialog.DialogCode.Accepted)
        saved = form.saved_record
        plan = self.plans.get(plan_form.saved_record.id)
        self.plans.save(PlanInput(plan.name, 3, 50000, 1, active=False), plan.id)
        edit = self.keep(StudentDialog(self.students, self.plans, saved))
        self.assertEqual(edit.fee.cents(), 42099)
        edit.name.setText("João atualizado")
        edit.active.setChecked(False)
        edit.save_button.click()
        current = self.students.get(saved.id)
        self.assertEqual(current.cpf, "52998224725")
        self.assertEqual(current.notes, "Observação mantida")
        self.assertEqual(current.monthly_fee_cents, 42099)
        self.assertFalse(current.active)

    def test_cancel_does_not_create_student(self):
        form = self.keep(StudentDialog(self.students, self.plans))
        form.name.setText("Não salvar")
        form.phone.setText("18999999999")
        form.reject()
        self.assertEqual(self.students.list(), [])

    def test_filters_profile_and_dashboard(self):
        self.students.save(StudentInput("João", "18999999999"))
        self.students.save(StudentInput("José", "18999999999", active=False))
        student = self.students.save(StudentInput("Álvaro", "18999999999", notes="<b>Texto literal</b>"))
        window = self.keep(MainWindow(DashboardService(self.sessions), self.paths, self.students, self.plans))
        window.show()
        window.resize(1050, 680)
        window.navigation.button(2).click()
        view = window.students
        self.app.processEvents()
        self.assertEqual(view.table.rowCount(), 3)
        view.search.setText("JOAO")
        view.refresh()
        self.assertEqual(view.table.rowCount(), 1)
        self.assertEqual(view.table.item(0, 0).text(), "João")
        view.clear_filters()
        view.letters.button(10).click()  # J
        self.assertEqual(view.table.rowCount(), 2)
        view.status.setCurrentIndex(1)
        self.assertEqual(view.table.rowCount(), 1)
        view.clear_filters()
        self.assertEqual(view.table.rowCount(), 3)
        for index in (2, 3):
            window.navigation.button(index).click()
            self.app.processEvents()
            scroll = window.pages.currentWidget()
            self.assertLessEqual(scroll.widget().minimumSizeHint().width(), scroll.viewport().width())
        window.navigation.button(0).click()
        self.assertEqual(window.dashboard.active_card.value_label.text(), "2")
        profile = self.keep(StudentProfile(student.id, self.students, self.plans))
        self.assertEqual(profile.name.text(), "Álvaro")
        self.assertEqual(profile.notes.text(), "<b>Texto literal</b>")

    def test_whatsapp_review_only_opens_on_click_and_handles_failure(self):
        student = self.students.save(StudentInput("João", "18999999999"))
        with patch("studio_fd.views.whatsapp.QDesktopServices.openUrl", return_value=True) as open_url:
            dialog = self.keep(WhatsAppDialog(student))
            open_url.assert_not_called()
            dialog.message.setPlainText("Olá João & Maria!\nPodemos conversar?")
            dialog.save_button.click()
            open_url.assert_called_once()
            url = open_url.call_args.args[0].toString()
            self.assertEqual(urlparse(url).path, "/5518999999999")
            self.assertEqual(parse_qs(urlparse(url).query)["text"], [dialog.message.toPlainText()])
            self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        with patch("studio_fd.views.whatsapp.QDesktopServices.openUrl", return_value=False):
            dialog = self.keep(WhatsAppDialog(student))
            dialog.save_button.click()
            self.assertIn("Não foi possível abrir", dialog.feedback.text())
            self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)
        with patch("studio_fd.views.whatsapp.QDesktopServices.openUrl") as open_url:
            dialog = self.keep(WhatsAppDialog(replace(student, phone="123")))
            dialog.save_button.click()
            open_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
