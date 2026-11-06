from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.util.exc import CommandError
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from studio_fd.database.base import Base
from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.models import Plan, Student
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.utils.paths import AppPaths


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.paths = AppPaths(Path(self.temp.name))
        self.paths.ensure_directories()
        self.engine = create_database_engine(self.paths.database)
        migrate_database(self.engine)
        self.sessions = create_session_factory(self.engine)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_initial_schema_matches_models(self):
        self.assertEqual(set(inspect(self.engine).get_table_names()), {"alembic_version", "plans", "students", "trainers", "settings", "appointments", "payments", "cash_entries", "contracts"})
        with self.engine.connect() as connection:
            self.assertEqual(compare_metadata(MigrationContext.configure(connection), Base.metadata), [])
            self.assertEqual(connection.scalar(text("PRAGMA integrity_check")), "ok")

    def test_reopening_preserves_students_and_counts_only_active(self):
        with self.sessions.begin() as session:
            session.add_all([Student(full_name="João Teste", phone="18999999999"), Student(full_name="Maria Teste", phone="", active=False)])
        self.engine.dispose()
        migrate_database(self.engine)
        self.assertEqual(DashboardService(self.sessions).summary().active_students, 1)
        with self.sessions() as session:
            self.assertEqual(session.get(Student, 1).full_name, "João Teste")

    def test_invalid_fee_due_day_and_missing_plan_are_rejected(self):
        for fields in ({"monthly_fee_cents": -1}, {"due_day": 32}, {"plan_id": 999}, {"full_name": " "}):
            with self.subTest(fields=fields), self.assertRaises(IntegrityError):
                with self.sessions.begin() as session:
                    session.add(Student(**({"full_name": "Aluno", "phone": ""} | fields)))

    def test_plan_values_and_relation(self):
        with self.sessions.begin() as session:
            plan = Plan(name="Plano de teste", workouts_per_week=3, price_cents=45000, duration_months=1)
            session.add(plan)
            session.flush()
            session.add(Student(full_name="Aluno", phone="", plan_id=plan.id, monthly_fee_cents=42000, due_day=10))
        with self.sessions() as session:
            student = session.get(Student, 1)
            self.assertEqual(student.plan.price_cents, 45000)
            self.assertEqual(student.monthly_fee_cents, 42000)
        with self.assertRaises(IntegrityError), self.sessions.begin() as session:
            session.execute(text("DELETE FROM plans"))

    def test_newer_database_is_refused_without_erasing_data(self):
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num='future_revision'"))
        with self.assertRaises(CommandError):
            migrate_database(self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), "future_revision")
        self.assertIn("students", inspect(self.engine).get_table_names())


if __name__ == "__main__":
    unittest.main()
