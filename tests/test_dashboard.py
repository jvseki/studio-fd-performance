from datetime import date
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.services.dashboard_service import DashboardService, next_due
from studio_fd.services.plan_service import PlanService
from studio_fd.services.records import PlanInput, StudentInput
from studio_fd.services.student_service import StudentService
from studio_fd.views.dashboard import DashboardView


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.engine = create_database_engine(Path(self.temp.name) / "teste.db")
        migrate_database(self.engine)
        self.sessions = create_session_factory(self.engine)
        self.students = StudentService(self.sessions)
        self.plans = PlanService(self.sessions)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_next_due_handles_month_end_and_year_turn(self):
        self.assertEqual(next_due(10, date(2026, 11, 5)), date(2026, 11, 10))
        self.assertEqual(next_due(5, date(2026, 11, 5)), date(2026, 11, 5))
        self.assertEqual(next_due(3, date(2026, 12, 5)), date(2027, 1, 3))
        self.assertEqual(next_due(31, date(2027, 2, 10)), date(2027, 2, 28))

    def test_summary_uses_only_active_students(self):
        plan = self.plans.save(PlanInput("Performance 3x", 3, 45000, 1))
        self.students.save(StudentInput("Ana", "18999999999", plan_id=plan.id, monthly_fee_cents=45000, due_day=6))
        self.students.save(StudentInput("Bruno", "18999999999", monthly_fee_cents=30000, due_day=20))
        self.students.save(StudentInput("Caio", "18999999999", monthly_fee_cents=99000, due_day=6, active=False))
        summary = DashboardService(self.sessions).summary(date(2026, 11, 5))
        self.assertEqual(summary.active_students, 2)
        self.assertEqual(summary.total_students, 3)
        self.assertEqual(summary.monthly_revenue_cents, 75000)
        self.assertEqual(summary.average_fee_cents, 37500)
        self.assertEqual(summary.due_this_week, 1)
        self.assertEqual([item.name for item in summary.upcoming], ["Ana", "Bruno"])
        self.assertEqual(summary.by_plan, [("Performance 3x", 1), ("Sem plano", 1)])

    def test_refresh_replaces_rows_instead_of_stacking(self):
        app = QApplication.instance() or QApplication([])
        for name in ("Ana", "Bia", "Caio"):
            self.students.save(StudentInput(name, "18999999999", due_day=10, monthly_fee_cents=100))
        view = DashboardView(DashboardService(self.sessions))
        view.show()
        for _ in range(3):
            view.refresh()
            app.processEvents()
        rows = [view.due_list.itemAt(index).widget() for index in range(view.due_list.count())]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row.isVisible() for row in rows))
        view.close()


if __name__ == "__main__":
    unittest.main()
