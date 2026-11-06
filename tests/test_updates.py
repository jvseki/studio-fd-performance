from contextlib import closing, ExitStack
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine
from studio_fd.services.update_service import prepare_update, confirm_version, read_installed_version, STATE_FILE
from studio_fd.utils.paths import AppPaths


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.paths = AppPaths(Path(self.temp.name))
        self.paths.ensure_directories()

    def tearDown(self):
        self.temp.cleanup()

    def create_database(self):
        engine = create_database_engine(self.paths.database)
        try:
            migrate_database(engine)
        finally:
            engine.dispose()
        with closing(sqlite3.connect(self.paths.database)) as db, db:
            db.execute("INSERT INTO students (full_name, phone, registered_on, active) VALUES (?, ?, ?, ?)",
                       ("Aluno da atualização", "18999999999", "2026-11-04", 1))

    def test_backup_restores_database_and_files_with_matching_hashes(self):
        self.create_database()
        confirm_version(self.paths, "0.2.0")
        (self.paths.contracts / "contrato.pdf").write_bytes(b"conteudo de teste")
        (self.paths.settings / "preferencias.json").write_text('{"tema":"escuro"}')
        (self.paths.backups / "antigo.zip").write_bytes(b"nao incluir")
        (self.paths.logs / "studio_fd.log").write_text("nao incluir")
        before = self.paths.database.read_bytes()
        archive_path = prepare_update(self.paths, "0.2.1")
        self.assertEqual(self.paths.database.read_bytes(), before)
        self.assertEqual(read_installed_version(self.paths), "0.2.0")
        with ZipFile(archive_path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["previous_version"], "0.2.0")
            self.assertEqual(manifest["schema_revision"], "0002")
            self.assertEqual(set(manifest["files"]), {"studio_fd.db", "contratos/contrato.pdf",
                                                     "configuracoes/preferencias.json", "configuracoes/" + STATE_FILE})
            for name, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
            restored = self.paths.root / "restaurado.db"
            restored.write_bytes(archive.read("studio_fd.db"))
        with closing(sqlite3.connect(restored)) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("SELECT full_name FROM students").fetchone()[0], "Aluno da atualização")
        confirm_version(self.paths, "0.2.1")
        self.assertIsNone(prepare_update(self.paths, "0.2.1"))
        self.assertEqual(len(list(self.paths.backups.glob("StudioFD_*.zip"))), 1)

    def test_fresh_install_and_unmarked_legacy_database(self):
        self.assertIsNone(prepare_update(self.paths, "0.2.1"))
        self.create_database()
        archive = prepare_update(self.paths, "0.2.1")
        self.assertTrue(archive.is_file())
        self.assertIsNone(read_installed_version(self.paths))
        confirm_version(self.paths, "0.2.1")
        self.assertIsNone(prepare_update(self.paths, "0.2.1"))

    def test_downgrade_and_invalid_marker_leave_data_untouched(self):
        self.create_database()
        before = self.paths.database.read_bytes()
        confirm_version(self.paths, "0.3.0")
        with self.assertRaisesRegex(ValueError, "0.3.0"):
            prepare_update(self.paths, "0.2.1")
        (self.paths.settings / STATE_FILE).write_text("invalid json")
        with self.assertRaisesRegex(ValueError, "versão dos dados"):
            prepare_update(self.paths, "0.2.1")
        self.assertEqual(self.paths.database.read_bytes(), before)
        self.assertEqual(list(self.paths.backups.iterdir()), [])

    def test_corruption_or_backup_write_failure_does_not_confirm_version(self):
        self.paths.database.write_bytes(b"invalid database")
        with self.assertRaises(sqlite3.DatabaseError):
            prepare_update(self.paths, "0.2.1")
        self.assertEqual(list(self.paths.backups.iterdir()), [])
        self.paths.database.unlink()
        self.create_database()
        confirm_version(self.paths, "0.2.0")
        with patch("studio_fd.services.update_service.ZipFile", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                prepare_update(self.paths, "0.2.1")
        self.assertEqual(read_installed_version(self.paths), "0.2.0")
        self.assertEqual(list(self.paths.backups.iterdir()), [])

    def test_backup_failure_stops_startup_before_migration(self):
        from studio_fd import app
        with ExitStack() as stack:
            for name in ("QApplication", "QLockFile", "QMessageBox", "RotatingFileHandler", "logging"):
                stack.enter_context(patch.object(app, name))
            stack.enter_context(patch.object(app.AppPaths, "default", return_value=self.paths))
            stack.enter_context(patch.object(app, "prepare_update", side_effect=OSError("disk full")))
            engine = stack.enter_context(patch.object(app, "create_database_engine"))
            migrate = stack.enter_context(patch.object(app, "migrate_database"))
            confirm = stack.enter_context(patch.object(app, "confirm_version"))
            self.assertEqual(app.run(), 1)
            engine.assert_not_called()
            migrate.assert_not_called()
            confirm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
