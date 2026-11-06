"""Exportação e restauração de um arquivo único (.fdbkp) com todos os dados.

O .fdbkp é um ZIP com:
    manifest.json       produto, formato, versão do app, revisão do banco, SHA-256 de cada arquivo
    studio_fd.db        cópia consistente do banco (API de backup do SQLite)
    contratos/...       PDFs dos contratos
    configuracoes/...   preferências locais

Restaurar acontece em duas fases para nunca perder dados:
1. stage_restore(): valida o arquivo inteiro, faz uma cópia de segurança dos
   dados atuais e extrai o backup para data/restauracao_pendente/.
2. apply_pending(): na próxima abertura, ANTES de conectar ao banco, troca os
   arquivos. Com o banco fechado, o Windows não bloqueia a substituição.
"""

from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile, ZIP_DEFLATED

from alembic.script import ScriptDirectory

from studio_fd.services.update_service import PRODUCT, STATE_FILE
from studio_fd.utils.paths import AppPaths, resource_root

EXTENSION = ".fdbkp"
FORMAT = 1
PENDING = "restauracao_pendente"
AUTO_FOLDER = "automaticos"
COUNTED_TABLES = {"students": "alunos", "payments": "mensalidades", "appointments": "agendamentos",
                  "contracts": "contratos", "cash_entries": "movimentações"}


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    created_at: datetime | None
    app_version: str | None
    schema_revision: str | None
    reason: str
    counts: dict[str, int] = field(default_factory=dict)
    files: int = 0


@dataclass(frozen=True)
class BackupFile:
    path: Path
    modified: datetime
    size: int
    automatic: bool


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_name(name: str) -> bool:
    parts = PurePosixPath(name).parts
    if not parts or name.startswith("/") or "\\" in name or ".." in parts or ":" in name:
        return False
    return name in ("manifest.json", "studio_fd.db") or parts[0] in ("contratos", "configuracoes")


def _counts(database: Path) -> dict[str, int]:
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {label: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table, label in COUNTED_TABLES.items() if table in tables}


def _known_revision(revision: str | None) -> bool:
    if revision is None:
        return False
    try:
        return ScriptDirectory(str(resource_root() / "migrations")).get_revision(revision) is not None
    except Exception:
        return False


class BackupService:
    def __init__(self, paths: AppPaths, app_version: str):
        self.paths = paths
        self.app_version = app_version

    @staticmethod
    def default_name(today: date | None = None) -> str:
        return f"StudioFD_Backup_{(today or date.today()):%Y-%m-%d}{EXTENSION}"

    # Exportar -----------------------------------------------------------
    def _data_files(self):
        for directory in (self.paths.contracts, self.paths.settings):
            if not directory.exists():
                continue
            for source in sorted(directory.rglob("*")):
                if source.is_symlink():
                    raise ValueError("O backup não aceita atalhos dentro das pastas de dados.")
                if source.is_file() and source.name != STATE_FILE and not source.name.endswith((".tmp", ".partial")):
                    yield source, source.relative_to(self.paths.root).as_posix()

    def export(self, destination: Path, reason: str = "manual") -> Path:
        destination = Path(destination)
        if destination.suffix.lower() not in (EXTENSION, ".zip"):
            destination = destination.with_name(destination.name + EXTENSION)
        if not self.paths.database.exists():
            raise ValueError("Ainda não há dados para exportar.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(destination.name + ".partial")
        partial.unlink(missing_ok=True)
        try:
            with TemporaryDirectory(prefix="backup-") as staging:
                snapshot = Path(staging) / "studio_fd.db"
                with closing(sqlite3.connect(self.paths.database.resolve().as_uri() + "?mode=ro", uri=True)) as source:
                    with closing(sqlite3.connect(snapshot)) as target:
                        source.backup(target)
                        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise ValueError("O banco não passou na verificação de integridade. Nada foi exportado.")
                        revision = target.execute("SELECT version_num FROM alembic_version").fetchone()
                manifest = {
                    "product": PRODUCT, "backup_format": FORMAT, "reason": reason,
                    "app_version": self.app_version, "schema_revision": revision[0] if revision else None,
                    "created_at": datetime.now(timezone.utc).isoformat(), "counts": _counts(snapshot), "files": {},
                }
                with ZipFile(partial, "x", compression=ZIP_DEFLATED) as archive:
                    for source_file, name in [(snapshot, "studio_fd.db"), *self._data_files()]:
                        archive.write(source_file, name)
                        manifest["files"][name] = _sha256(source_file)
                    archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            self.inspect(partial)  # relê e confere tudo antes de entregar
            partial.replace(destination)
            return destination
        except Exception:
            partial.unlink(missing_ok=True)
            raise

    # Validar -----------------------------------------------------------
    def inspect(self, path: Path) -> BackupInfo:
        path = Path(path)
        try:
            with ZipFile(path) as archive:
                names = archive.namelist()
                if "manifest.json" not in names or "studio_fd.db" not in names:
                    raise ValueError("Esse arquivo não é um backup do Studio FD Performance.")
                if any(not _safe_name(name) for name in names if not name.endswith("/")):
                    raise ValueError("O backup contém arquivos fora da estrutura esperada e foi recusado.")
                try:
                    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ValueError("O manifesto do backup está danificado.") from error
                if manifest.get("product") != PRODUCT:
                    raise ValueError("Esse arquivo não pertence ao Studio FD Performance.")
                if manifest.get("backup_format", 0) > FORMAT:
                    raise ValueError("Esse backup foi criado por uma versão mais nova do Studio. Atualize o programa antes de restaurar.")
                files = manifest.get("files") or {}
                if set(files) != {name for name in names if name != "manifest.json" and not name.endswith("/")}:
                    raise ValueError("A lista de arquivos do backup não confere. O arquivo pode estar incompleto.")
                with TemporaryDirectory(prefix="verificar-") as staging:
                    for name, expected in files.items():
                        digest = hashlib.sha256()
                        with archive.open(name) as reader:
                            for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                                digest.update(chunk)
                        if digest.hexdigest() != expected:
                            raise ValueError("Um dos arquivos do backup está corrompido (verificação SHA-256).")
                    database = Path(archive.extract("studio_fd.db", staging))
                    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
                        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise ValueError("O banco dentro do backup não passou na verificação de integridade.")
                        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
                    revision = row[0] if row else None
                    if not _known_revision(revision):
                        raise ValueError("Esse backup usa uma estrutura de banco desconhecida por esta versão. Atualize o Studio antes de restaurar.")
                    counts = _counts(database)
        except BadZipFile as error:
            raise ValueError("O arquivo está danificado ou não é um backup do Studio.") from error
        except sqlite3.DatabaseError as error:
            raise ValueError("O banco dentro do backup está danificado.") from error
        created = manifest.get("created_at")
        return BackupInfo(path, datetime.fromisoformat(created) if created else None,
                          manifest.get("app_version") or manifest.get("target_version"), revision,
                          manifest.get("reason", "manual"), counts,
                          sum(1 for name in files if name.startswith("contratos/")))

    # Restaurar ---------------------------------------------------------
    def stage_restore(self, path: Path) -> Path:
        """Valida, protege os dados atuais e deixa a restauração pronta para a próxima abertura.
        Devolve o caminho da cópia de segurança dos dados atuais."""
        self.inspect(path)
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safety = self.export(self.paths.backups / f"StudioFD_AntesDeRestaurar_{stamp}{EXTENSION}", reason="before-restore")
        pending = self.paths.root / PENDING
        if pending.exists():
            shutil.rmtree(pending)
        pending.mkdir()
        try:
            with ZipFile(path) as archive:
                for name in archive.namelist():
                    if name != "manifest.json" and not name.endswith("/") and _safe_name(name):
                        archive.extract(name, pending)
            (pending / "ready.json").write_text(json.dumps({"source": str(path), "safety_backup": str(safety)}), encoding="utf-8")
        except Exception:
            shutil.rmtree(pending, ignore_errors=True)
            raise
        return safety

    @staticmethod
    def has_pending(paths: AppPaths) -> bool:
        return (paths.root / PENDING / "ready.json").exists()

    @staticmethod
    def apply_pending(paths: AppPaths) -> bool:
        """Chamado na abertura, antes de criar a conexão com o banco."""
        pending = paths.root / PENDING
        if not (pending / "ready.json").exists():
            if pending.exists():
                shutil.rmtree(pending, ignore_errors=True)  # extração interrompida: descarta
            return False
        for suffix in ("-wal", "-shm", "-journal"):
            Path(str(paths.database) + suffix).unlink(missing_ok=True)
        os.replace(pending / "studio_fd.db", paths.database)
        restored_contracts = pending / "contratos"
        old = paths.root / "contratos_anteriores"
        if old.exists():
            shutil.rmtree(old)
        if paths.contracts.exists():
            paths.contracts.rename(old)
        if restored_contracts.exists():
            restored_contracts.rename(paths.contracts)
        else:
            paths.contracts.mkdir()
        shutil.rmtree(old, ignore_errors=True)
        restored_settings = pending / "configuracoes"
        if restored_settings.exists():
            for source in restored_settings.rglob("*"):
                if source.is_file() and source.name != STATE_FILE:
                    target = paths.settings / source.relative_to(restored_settings)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
        shutil.rmtree(pending, ignore_errors=True)
        return True

    # Automáticos -------------------------------------------------------
    def auto_backup(self, keep: int = 10, today: date | None = None) -> Path | None:
        """Um backup por dia, guardando os mais recentes."""
        folder = self.paths.backups / AUTO_FOLDER
        target = folder / f"StudioFD_Auto_{(today or date.today()):%Y-%m-%d}{EXTENSION}"
        if target.exists() or not self.paths.database.exists():
            return None
        result = self.export(target, reason="automatic")
        automatic = sorted(folder.glob(f"StudioFD_Auto_*{EXTENSION}"), reverse=True)
        for old in automatic[keep:]:
            old.unlink(missing_ok=True)
        return result

    def list_backups(self) -> list[BackupFile]:
        found = []
        for folder, automatic in ((self.paths.backups, False), (self.paths.backups / AUTO_FOLDER, True)):
            if folder.exists():
                for item in folder.iterdir():
                    if item.is_file() and item.suffix.lower() in (EXTENSION, ".zip"):
                        stat = item.stat()
                        found.append(BackupFile(item, datetime.fromtimestamp(stat.st_mtime), stat.st_size, automatic))
        return sorted(found, key=lambda item: item.modified, reverse=True)
