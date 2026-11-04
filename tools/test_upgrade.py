"""Instala a versão anterior, atualiza e reinstala com cadastros fictícios isolados."""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4
import winreg
from zipfile import ZipFile

from test_frozen import launch_and_close

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from studio_fd import __version__

KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{A71B7309-A7B7-4BDA-A1EC-26B673AEBC84}_is1"


def installed():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY):
            return True
    except FileNotFoundError:
        return False


def file_hash(path):
    if not path.exists():
        return None
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run_installer(installer, target, log):
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    subprocess.run([str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOICONS",
                    "/TASKS=", f"/DIR={target}", f"/LOG={log}"], startupinfo=startup, check=True, timeout=180)


def rows(database):
    with closing(sqlite3.connect(database)) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return {name: db.execute(f"SELECT * FROM {name} ORDER BY id").fetchall() for name in ("plans", "students")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", default="0.2.0")
    args = parser.parse_args()
    if installed():
        raise RuntimeError("Há um Studio instalado nessa conta. Use uma conta de teste; nenhuma instalação foi alterada.")
    old = (PROJECT / "release" / f"StudioFDPerformance-Setup-{args.previous}.exe").resolve(strict=True)
    new = (PROJECT / "release" / f"StudioFDPerformance-Setup-{__version__}.exe").resolve(strict=True)
    root = (PROJECT / "build" / f"upgrade-check-{uuid4().hex[:8]}").resolve()
    root.relative_to((PROJECT / "build").resolve())
    target, data = root / "program", root / "data"
    root.mkdir()
    database = data / "studio_fd.db"
    real_database = Path(os.environ["LOCALAPPDATA"]) / "StudioFDPerformance/data/studio_fd.db"
    real_hash = file_hash(real_database)
    executable = target / "Studio FD Performance.exe"
    try:
        print(f"Instalando {args.previous} em {target}", flush=True)
        run_installer(old, target, root / "install-old.log")
        launch_and_close(executable, data)
        with closing(sqlite3.connect(database)) as db, db:
            db.execute("INSERT INTO plans (name, workouts_per_week, price_cents, duration_months, active) VALUES ('Plano teste', 3, 35000, 1, 1)")
            db.execute("INSERT INTO students (full_name, phone, registered_on, active, plan_id, monthly_fee_cents, due_day) VALUES ('Aluno teste atualização', '18999999999', '2026-11-04', 1, 1, 32000, 10)")
        contract = data / "contratos/teste.pdf"
        contract.write_bytes(b"Contrato ficticio para teste de preservacao")
        expected = rows(database)
        print(f"Atualizando para {__version__}...", flush=True)
        run_installer(new, target, root / "install-new.log")
        launch_and_close(executable, data)
        assert rows(database) == expected
        marker = json.loads((data / "configuracoes/versao_instalada.json").read_text())
        assert marker["version"] == __version__
        backups = list((data / "backups").glob("StudioFD_*.zip"))
        assert len(backups) == 1
        with ZipFile(backups[0]) as archive:
            assert archive.testzip() is None
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["target_version"] == __version__
            for name, digest in manifest["files"].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == digest
            restored = root / "restored.db"
            restored.write_bytes(archive.read("studio_fd.db"))
            assert rows(restored) == expected
            assert archive.read("contratos/teste.pdf") == contract.read_bytes()
        print("Reabrindo e reinstalando a mesma versão...", flush=True)
        launch_and_close(executable, data)
        run_installer(new, target, root / "reinstall.log")
        launch_and_close(executable, data)
        assert rows(database) == expected
        assert list((data / "backups").glob("StudioFD_*.zip")) == backups
        log = (data / "logs/studio_fd.log").read_text(encoding="utf-8")
        assert "ERROR" not in log and "Traceback" not in log
    finally:
        uninstaller = target / "unins000.exe"
        if uninstaller.exists():
            print("Removendo somente a instalação de teste...", flush=True)
            run_installer(uninstaller, target, root / "uninstall.log")
        assert not executable.exists(), "O executável de teste permaneceu após desinstalar."
        assert not installed(), "O registro da instalação de teste permaneceu."
        assert file_hash(real_database) == real_hash, "O banco real mudou durante a verificação."
    assert rows(database) == expected
    assert backups[0].is_file()
    (root / "RESULTADO.txt").write_text(
        f"OK: {args.previous} -> {__version__}; dados, plano, mensalidade negociada, contrato e backup preservados; "
        "reabertura, reinstalação e desinstalação verificadas; banco real inalterado.\n", encoding="utf-8")
    print(f"OK: atualização completa validada. Evidências: {root}", flush=True)


if __name__ == "__main__":
    main()
