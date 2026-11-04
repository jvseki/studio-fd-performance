from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.release import generate, read_version, validate_release, write_metadata
from studio_fd.utils.versioning import version_tuple


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.project = Path(self.temp.name)
        (self.project / "studio_fd").mkdir()
        (self.project / "studio_fd/__init__.py").write_text('__version__ = "0.2.0"\n', encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_invalid_versions_and_existing_deliveries_are_refused(self):
        for version in ("0.2", "0.02.1", "1.0.0-beta", "../0.2.1", "65536.0.0", "0.2.0", "0.1.9"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                validate_release(self.project, version)
        installer = validate_release(self.project, "0.2.1")
        installer.parent.mkdir()
        installer.write_bytes(b"old delivery")
        with self.assertRaises(ValueError):
            validate_release(self.project, "0.2.1")
        self.assertEqual(installer.read_bytes(), b"old delivery")
        self.assertGreater(version_tuple("0.10.0"), version_tuple("0.9.9"))

    def test_metadata_uses_same_numeric_version(self):
        write_metadata(self.project, "2.10.31")
        info = (self.project / "build/windows_version_info.txt").read_text()
        self.assertIn("filevers=(2, 10, 31, 0)", info)
        self.assertIn("'ProductVersion', '2.10.31'", info)
        self.assertIn('#define AppVersion "2.10.31"', (self.project / "build/release_version.iss").read_text())

    def test_failed_check_restores_version_and_does_not_publish(self):
        compiler = self.project / "compiler.exe"
        compiler.write_bytes(b"stub")
        with patch("tools.release.subprocess.run", side_effect=subprocess.CalledProcessError(1, "test")):
            with self.assertRaises(subprocess.CalledProcessError):
                generate(self.project, "0.2.1", "Teste", compiler)
        self.assertEqual(read_version(self.project), "0.2.0")
        self.assertFalse((self.project / "release").exists())


if __name__ == "__main__":
    unittest.main()
