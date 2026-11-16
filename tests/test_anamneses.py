"""Anamneses em PDF: cópia interna, validação, consistência e backup. Só dados fictícios."""

from datetime import date
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from sqlalchemy import func, select

from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.models import Anamnesis
from studio_fd.services.anamnesis_service import AnamnesisService
from studio_fd.services.backup_service import BackupService
from studio_fd.services.records import StudentInput
from studio_fd.services.student_service import StudentService
from studio_fd.services.update_service import prepare_update
from studio_fd.utils.paths import AppPaths

FAKE_PDF = b"%PDF-1.4\n% anamnese ficticia de teste\n%%EOF\n"


class AnamnesisTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.paths = AppPaths(self.base / "data")
        self.paths.ensure_directories()
        self.engine = create_database_engine(self.paths.database)
        migrate_database(self.engine)
        self.sessions = create_session_factory(self.engine)
        self.service = AnamnesisService(self.sessions, self.paths)
        self.student = StudentService(self.sessions).save(StudentInput("Aluno Fictício", "18999999999")).id
        self.source = self.base / "Downloads" / "anamnese.pdf"
        self.source.parent.mkdir()
        self.source.write_bytes(FAKE_PDF)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def count(self):
        with self.sessions() as session:
            return session.scalar(select(func.count(Anamnesis.id)))

    def test_copy_survives_original_removal_and_keeps_history(self):
        first = self.service.add(self.student, self.source, date(2026, 11, 1), "Primeira avaliação")
        second = self.service.add(self.student, self.source, date(2026, 11, 10))
        self.source.unlink()
        records = self.service.for_student(self.student)
        self.assertEqual([r.id for r in records], [second.id, first.id])
        stored = self.service.file(first)
        self.assertTrue(stored.is_relative_to(self.paths.anamneses.resolve()))
        self.assertEqual(stored.read_bytes(), FAKE_PDF)
        self.assertEqual(first.sha256, hashlib.sha256(FAKE_PDF).hexdigest())
        self.assertEqual(first.original_name, "anamnese.pdf")
        self.assertNotEqual(first.file_path, second.file_path)
        copy = self.service.save_copy(first, self.base / "copia.pdf")
        self.assertEqual(copy.read_bytes(), FAKE_PDF)
        self.service.delete(first.id)
        self.assertFalse(stored.exists())
        self.assertTrue((self.paths.anamneses / "_removidos" / stored.name).exists())
        self.assertEqual(len(self.service.for_student(self.student)), 1)

    def test_invalid_files_are_rejected_without_record(self):
        fake = self.base / "falso.pdf"
        fake.write_text("não é pdf")
        empty = self.base / "vazio.pdf"
        empty.write_bytes(b"")
        other = self.base / "anamnese.docx"
        other.write_bytes(FAKE_PDF)
        for path, message in ((fake, "não é um PDF"), (empty, "vazio"), (other, ".pdf"), (self.base / "sumiu.pdf", "não foi encontrado")):
            with self.subTest(path=path.name), self.assertRaisesRegex(ValueError, message):
                self.service.add(self.student, path)
        with self.assertRaisesRegex(ValueError, "não foi encontrado"):
            self.service.add(999, self.source)
        self.assertEqual(self.count(), 0)
        self.assertEqual(list(self.paths.anamneses.rglob("*.pdf")), [])

    def test_database_failure_removes_copied_file(self):
        with patch("studio_fd.services.anamnesis_service.Anamnesis", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                self.service.add(self.student, self.source)
        self.assertEqual(self.count(), 0)
        self.assertEqual(list(self.paths.anamneses.rglob("*.pdf*")), [])

    def test_backup_restore_and_update_snapshot_include_anamneses(self):
        record = self.service.add(self.student, self.source)
        backups = BackupService(self.paths, "0.4.0")
        exported = backups.export(self.base / "backup.fdbkp")
        with ZipFile(exported) as archive:
            self.assertIn(f"anamneses/{record.file_path}", archive.namelist())
        self.assertEqual(backups.inspect(exported).counts["anamneses"], 1)
        self.service.delete(record.id)
        backups.stage_restore(exported)
        self.engine.dispose()
        BackupService.apply_pending(self.paths)
        migrate_database(self.engine)
        restored = self.service.for_student(self.student)
        self.assertEqual(len(restored), 1)
        self.assertEqual(hashlib.sha256(self.service.file(restored[0]).read_bytes()).hexdigest(), record.sha256)
        snapshot = prepare_update(self.paths, "99.0.0")
        with ZipFile(snapshot) as archive:
            self.assertIn(f"anamneses/{record.file_path}", archive.namelist())


if __name__ == "__main__":
    unittest.main()
