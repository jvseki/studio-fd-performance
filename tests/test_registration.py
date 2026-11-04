from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import parse_qs, urlparse

from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.plan_service import PlanService
from studio_fd.services.records import PlanInput, StudentInput
from studio_fd.services.student_service import StudentService
from studio_fd.services.whatsapp_service import chat_url
from studio_fd.utils.formatting import brl, normalize_phone


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.engine = create_database_engine(Path(self.temp.name) / "test.db")
        migrate_database(self.engine)
        self.sessions = create_session_factory(self.engine)
        self.students = StudentService(self.sessions)
        self.plans = PlanService(self.sessions)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_create_edit_inactivate_and_reopen(self):
        data = StudentInput("  João   Silva  ", "(18) 99999-9999", cpf="529.982.247-25", notes="Observação de teste")
        student = self.students.save(data)
        self.assertEqual(student.full_name, "João Silva")
        self.assertEqual(student.phone, "5518999999999")
        self.assertEqual(student.cpf, "52998224725")
        self.assertEqual(student.registered_on, date.today())
        self.students.save(replace(data, active=False, address="Rua de teste"), student.id)
        self.engine.dispose()
        reread = self.students.get(student.id)
        self.assertFalse(reread.active)
        self.assertEqual(reread.address, "Rua de teste")
        self.assertEqual(reread.registered_on, student.registered_on)
        self.assertEqual(DashboardService(self.sessions).summary().active_students, 0)
        self.assertEqual(len(self.students.list()), 1)

    def test_search_accents_letter_status_and_literal_wildcards(self):
        for name in ("João Silva", "José Carlos", "Álvaro", "Ana 100%", "Ana Silva"):
            self.students.save(StudentInput(name, "18999999999", active=name != "José Carlos"))
        self.assertEqual([s.full_name for s in self.students.list("JOAO")], ["João Silva"])
        self.assertEqual(len(self.students.list(letter="J")), 2)
        self.assertEqual(len(self.students.list(letter="J", active=True)), 1)
        self.assertEqual(len(self.students.list(letter="A")), 3)
        self.assertEqual([s.full_name for s in self.students.list("%")], ["Ana 100%"])
        self.assertEqual([s.full_name for s in self.students.list("jose", active=False)], ["José Carlos"])

    def test_validation_prevents_partial_writes_and_duplicate_cpf(self):
        data = StudentInput("Aluno teste", "18999999999", cpf="52998224725")
        student = self.students.save(data)
        for invalid in (
            replace(data, full_name=" "), replace(data, phone="999"),
            replace(data, cpf="11111111111"), replace(data, cpf="52998224724"),
            replace(data, monthly_fee_cents=-1), replace(data, monthly_fee_cents=1.5),
            replace(data, due_day=32), replace(data, birth_date=date.today() + timedelta(days=1)),
            replace(data, plan_id=999),
        ):
            with self.subTest(data=invalid), self.assertRaises(ValueError):
                self.students.save(invalid, student.id)
        self.assertEqual(self.students.get(student.id).full_name, "Aluno teste")
        with self.assertRaisesRegex(ValueError, "CPF já"):
            self.students.save(replace(data, full_name="Outro aluno"))
        self.students.save(replace(data, full_name="Nome atualizado"), student.id)
        self.students.save(replace(data, full_name="Sem CPF 1", cpf=""))
        self.students.save(replace(data, full_name="Sem CPF 2", cpf=None))
        self.assertEqual(len(self.students.list()), 3)

    def test_plan_change_preserves_negotiated_fee_and_inactive_assignment(self):
        plan_data = PlanInput("3 vezes", 3, 45000, 1)
        plan = self.plans.save(plan_data)
        data = StudentInput("Aluno", "18999999999", plan_id=plan.id, monthly_fee_cents=42000, due_day=10)
        student = self.students.save(data)
        self.plans.save(replace(plan_data, price_cents=50000, active=False), plan.id)
        self.assertEqual(self.students.get(student.id).monthly_fee_cents, 42000)
        self.students.save(replace(data, notes="Edição permitida"), student.id)
        with self.assertRaisesRegex(ValueError, "inativo"):
            self.students.save(replace(data, full_name="Novo aluno"))
        other = self.plans.save(PlanInput("2 vezes", 2, 32000, 3))
        moved = self.students.save(replace(data, plan_id=other.id), student.id)
        self.assertEqual(moved.plan_name, "2 vezes")
        self.assertEqual(moved.monthly_fee_cents, 42000)
        removed = self.students.save(replace(data, plan_id=None), student.id)
        self.assertIsNone(removed.plan_name)

    def test_plan_validation(self):
        valid = PlanInput("Plano", 3, 45000, 1)
        for invalid in (replace(valid, name=""), replace(valid, workouts_per_week=8), replace(valid, price_cents=-1), replace(valid, duration_months=0)):
            with self.subTest(data=invalid), self.assertRaises(ValueError):
                self.plans.save(invalid)
        self.assertEqual(self.plans.list(), [])

    def test_whatsapp_normalizes_once_and_encodes_text(self):
        message = "Olá, João! Valor R$ 450,00 & detalhes?\nTudo bem? #Studio"
        for phone in ("(18) 99999-9999", "+55 (18) 99999-9999", "5518999999999"):
            parsed = urlparse(chat_url(phone, message))
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "wa.me")
            self.assertEqual(parsed.path, "/5518999999999")
            self.assertEqual(parse_qs(parsed.query)["text"], [message])
        self.assertEqual(normalize_phone("(55) 99999-9999"), "5555999999999")
        self.assertEqual(normalize_phone("(18) 3722-1234"), "551837221234")
        with self.assertRaises(ValueError):
            chat_url("5518999999999&other=1")
        with self.assertRaises(ValueError):
            chat_url("18999999999", "a" * 2001)
        self.assertEqual(brl(123456), "R$ 1.234,56")


if __name__ == "__main__":
    unittest.main()
