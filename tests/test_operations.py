"""Regras de negócio da agenda, financeiro, caixa, contratos e backup."""

from datetime import date, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.services.agenda_service import AgendaService
from studio_fd.services.backup_service import BackupService
from studio_fd.services.cash_service import CashService
from studio_fd.services.contract_service import ContractService
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.finance_service import FinanceService
from studio_fd.services.records import CashInput, StudentInput
from studio_fd.services.report_service import ReportService
from studio_fd.services.settings_service import SettingsService
from studio_fd.services.student_service import StudentService
from studio_fd.utils.paths import AppPaths

MONDAY = date(2026, 11, 9)


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.paths = AppPaths(Path(self.temp.name) / "data")
        self.paths.ensure_directories()
        self.engine = create_database_engine(self.paths.database)
        migrate_database(self.engine)
        self.sessions = create_session_factory(self.engine)
        self.students = StudentService(self.sessions)
        self.agenda = AgendaService(self.sessions)
        self.ids = [self.students.save(StudentInput(name, "18999999999", monthly_fee_cents=45000, due_day=5)).id
                    for name in ("Ana", "Bruno", "Carla")]

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_slot_accepts_two_students_and_refuses_the_third(self):
        self.agenda.book(self.ids[0], MONDAY, "07:00")
        self.agenda.book(self.ids[1], MONDAY, "07:00")
        with self.assertRaisesRegex(ValueError, "Este horário já atingiu o limite de 2 alunos."):
            self.agenda.book(self.ids[2], MONDAY, "07:00")
        row = next(row for row in self.agenda.day(MONDAY) if row.time == "07:00")
        self.assertEqual(row.booked, 2)
        self.assertEqual([item.student_name for _trainer, item in row.cells], ["Ana", "Bruno"])

    def test_same_student_twice_and_busy_trainer_are_refused(self):
        self.agenda.book(self.ids[0], MONDAY, "08:00", trainer_id=1)
        with self.assertRaisesRegex(ValueError, "já está agendado"):
            self.agenda.book(self.ids[0], MONDAY, "08:00")
        with self.assertRaisesRegex(ValueError, "Personal 1 já tem aluno"):
            self.agenda.book(self.ids[1], MONDAY, "08:00", trainer_id=1)

    def test_weekly_repeat_skips_full_weeks_and_frees_cancelled(self):
        full = MONDAY + timedelta(weeks=1)
        self.agenda.book(self.ids[1], full, "18:00")
        self.agenda.book(self.ids[2], full, "18:00")
        result = self.agenda.book(self.ids[0], MONDAY, "18:00", repeat_weeks=2)
        self.assertEqual(result.created, [MONDAY, MONDAY + timedelta(weeks=2)])
        self.assertEqual([day for day, _reason in result.skipped], [full])
        self.assertEqual(self.agenda.habitual(self.ids[0], MONDAY), ["Segunda 18:00"])
        cancelled = next(item for _t, item in next(r for r in self.agenda.day(full) if r.time == "18:00").cells if item)
        self.agenda.set_status(cancelled.id, "cancelado")
        self.agenda.book(self.ids[0], full, "18:00")
        self.assertEqual(self.agenda.remove_future_series(self.agenda.for_student(self.ids[0], MONDAY)[0].id), 3)

    def test_trainer_with_future_appointments_cannot_be_deactivated(self):
        settings = SettingsService(self.sessions)
        self.agenda.book(self.ids[0], date.today() + timedelta(days=1), "07:00", trainer_id=2)
        with self.assertRaisesRegex(ValueError, "Remaneje"):
            settings.save_trainer("Personal 2", False, 2)
        settings.save_trainer("Douglas", True, 1)
        self.assertEqual([t.name for t in settings.trainers()], ["Douglas", "Personal 2"])
        with self.assertRaisesRegex(ValueError, "fechamento"):
            settings.save_hours("10:00", "09:00", 60)
        self.assertEqual(settings.save_hours("07:00", "09:00", 30).slots(), ["07:00", "07:30", "08:00", "08:30"])

    def test_payment_cycle_keeps_cash_in_sync(self):
        finance, cash = FinanceService(self.sessions), CashService(self.sessions)
        month = date(2026, 10, 1)
        self.assertEqual(finance.generate(month), 3)
        self.assertEqual(finance.generate(month), 0)
        today = date(2026, 10, 7)
        records = finance.month(month, today)
        self.assertEqual({item.status for item in records}, {"Atrasado"})
        finance.register(records[0].id, date(2026, 10, 6), "Pix")
        self.assertEqual(cash.totals(month, today).income_cents, 45000)
        entry = cash.entries(month, today)[0]
        with self.assertRaisesRegex(ValueError, "Desfaça o pagamento"):
            cash.delete(entry.id)
        with self.assertRaisesRegex(ValueError, "Desfaça o pagamento"):
            finance.delete(records[0].id)
        summary = finance.summary(month, today)
        self.assertEqual((summary.paid, summary.overdue, summary.received_cents), (1, 2, 45000))
        finance.undo(records[0].id)
        self.assertEqual(cash.totals(month, today).income_cents, 0)
        cash.add(CashInput(today, "Conta de energia", "Energia", "saida", 21000, "Pix"))
        self.assertEqual(cash.totals(month, today).balance_cents, -21000)
        report = ReportService(self.sessions).build(month)
        self.assertEqual(report.current.expense_cents, 21000)
        self.assertEqual(report.expenses_by_category, [("Energia", 21000)])

    def test_dashboard_counts_today_agenda(self):
        self.agenda.book(self.ids[0], date.today(), "06:00")
        summary = DashboardService(self.sessions).summary()
        self.assertEqual(summary.today_booked, 1)
        self.assertEqual(summary.today_capacity, 30)
        self.assertEqual(summary.today_rows[0], ("06:00", ["Ana", None]))

    def test_contract_pdf_is_copied_and_removed_safely(self):
        contracts = ContractService(self.sessions, self.paths)
        source = Path(self.temp.name) / "assinado.pdf"
        source.write_bytes(b"%PDF-1.4 teste")
        record = contracts.add(self.ids[0], "presencial", date(2026, 11, 1), source, "Via assinada")
        stored = contracts.file(record)
        self.assertTrue(stored.is_relative_to(self.paths.contracts.resolve()))
        self.assertEqual(stored.read_bytes(), b"%PDF-1.4 teste")
        fake = Path(self.temp.name) / "falso.pdf"
        fake.write_text("não é pdf")
        with self.assertRaisesRegex(ValueError, "não é um PDF"):
            contracts.add(self.ids[0], "online", date(2026, 11, 1), fake)
        contracts.delete(record.id)
        self.assertFalse(stored.exists())
        self.assertTrue((self.paths.contracts / "_removidos" / stored.name).exists())

    def test_backup_round_trip_and_rejections(self):
        contracts = ContractService(self.sessions, self.paths)
        source = Path(self.temp.name) / "c.pdf"
        source.write_bytes(b"%PDF-1.7 original")
        contracts.add(self.ids[0], "online", date(2026, 11, 1), source)
        backups = BackupService(self.paths, "0.3.0")
        exported = backups.export(Path(self.temp.name) / "saida" / backups.default_name(date(2026, 11, 5)))
        self.assertEqual(exported.name, "StudioFD_Backup_2026-11-05.fdbkp")
        info = backups.inspect(exported)
        self.assertEqual((info.counts["alunos"], info.files, info.schema_revision), (3, 1, "0002"))

        # Dados mudam depois do backup; a restauração deve voltar ao estado salvo.
        self.students.save(StudentInput("Depois", "18999999999"))
        safety = backups.stage_restore(exported)
        self.assertTrue(safety.exists())
        self.assertEqual(backups.inspect(safety).counts["alunos"], 4)
        self.engine.dispose()
        self.assertTrue(BackupService.apply_pending(self.paths))
        self.assertFalse(BackupService.has_pending(self.paths))
        migrate_database(self.engine)
        self.assertEqual(len(StudentService(self.sessions).list()), 3)
        self.assertEqual(len(list(self.paths.contracts.rglob("*.pdf"))), 1)

        tampered = Path(self.temp.name) / "alterado.fdbkp"
        with ZipFile(exported) as original, ZipFile(tampered, "w") as copy:
            for item in original.namelist():
                data = original.read(item)
                copy.writestr(item, data + b"x" if item.startswith("contratos/") else data)
        with self.assertRaisesRegex(ValueError, "corrompido"):
            backups.inspect(tampered)
        foreign = Path(self.temp.name) / "outro.fdbkp"
        with ZipFile(foreign, "w") as archive:
            archive.writestr("manifest.json", json.dumps({"product": "outro"}))
            archive.writestr("studio_fd.db", b"")
        with self.assertRaisesRegex(ValueError, "não pertence"):
            backups.inspect(foreign)
        (Path(self.temp.name) / "texto.fdbkp").write_text("nada")
        with self.assertRaisesRegex(ValueError, "danificado"):
            backups.inspect(Path(self.temp.name) / "texto.fdbkp")

    def test_automatic_backup_runs_once_per_day_and_prunes(self):
        backups = BackupService(self.paths, "0.3.0")
        for offset in range(4):
            self.assertIsNotNone(backups.auto_backup(keep=2, today=date(2026, 11, 1 + offset)))
        self.assertIsNone(backups.auto_backup(keep=2, today=date(2026, 11, 4)))
        names = sorted(item.path.name for item in backups.list_backups() if item.automatic)
        self.assertEqual(names, ["StudioFD_Auto_2026-11-03.fdbkp", "StudioFD_Auto_2026-11-04.fdbkp"])


if __name__ == "__main__":
    unittest.main()
