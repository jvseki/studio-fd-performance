"""Protege os dados antes da primeira abertura de uma nova versão.

A cópia é feita antes de migrações e a versão só é confirmada após a inicialização.
Não substitui a futura tela de exportação e restauração de backups.
"""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

from studio_fd.utils.paths import AppPaths
from studio_fd.utils.versioning import version_tuple

PRODUCT = "studio-fd-performance"
STATE_FILE = "versao_instalada.json"


def read_installed_version(paths: AppPaths) -> str | None:
    marker = paths.settings / STATE_FILE
    if not marker.exists():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        if data["product"] != PRODUCT:
            raise ValueError("Produto incorreto")
        version_tuple(data["version"])
        return data["version"]
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError("Não foi possível ler a versão dos dados. Confira configuracoes/versao_instalada.json antes de atualizar.") from error


def _source_files(paths: AppPaths):
    for directory in (paths.contracts, paths.settings):
        if directory.is_symlink() or directory.is_junction():
            raise ValueError("A cópia de atualização não aceita links em contratos ou configurações.")
        for source in sorted(directory.rglob("*")):
            if source.is_symlink() or (hasattr(source, "is_junction") and source.is_junction()):
                raise ValueError("A cópia de atualização não aceita links em contratos ou configurações.")
            if source.is_file():
                source.resolve().relative_to(paths.root.resolve())
                yield source, source.relative_to(paths.root).as_posix()


def prepare_update(paths: AppPaths, new_version: str) -> Path | None:
    current = version_tuple(new_version)
    previous = read_installed_version(paths)
    if previous is not None and version_tuple(previous) > current:
        raise ValueError(f"Esses dados já foram abertos pela versão {previous}. Use essa versão ou uma mais recente.")
    if previous == new_version or not paths.database.exists():
        return None

    paths.ensure_directories()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    token = uuid4().hex[:8]
    destination = paths.backups / f"StudioFD_Antes_{new_version}_{stamp}_{token}.zip"
    partial = destination.with_suffix(".zip.partial")
    try:
        with TemporaryDirectory(prefix="snapshot-", dir=paths.backups) as staging:
            snapshot = Path(staging) / "studio_fd.db"
            with closing(sqlite3.connect(paths.database.resolve().as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(snapshot)) as target:
                    source.backup(target)
                    if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("O banco não passou na verificação. A atualização foi interrompida.")
                    revision = target.execute("SELECT version_num FROM alembic_version").fetchone()
            files = [(snapshot, "studio_fd.db"), *_source_files(paths)]
            manifest = {"product": PRODUCT, "backup_format": 1, "reason": "before-update",
                        "previous_version": previous, "target_version": new_version,
                        "schema_revision": revision[0] if revision else None,
                        "created_at": datetime.now(timezone.utc).isoformat(), "files": {}}
            with ZipFile(partial, "x", compression=ZIP_DEFLATED) as archive:
                for source_file, name in files:
                    digest = hashlib.sha256()
                    with source_file.open("rb") as reader, archive.open(name, "w") as writer:
                        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                            digest.update(chunk)
                            writer.write(chunk)
                    manifest["files"][name] = digest.hexdigest()
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            with ZipFile(partial) as archive:
                if archive.testzip() is not None:
                    raise ValueError("A cópia de segurança não passou na verificação.")
            partial.replace(destination)
        return destination
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def confirm_version(paths: AppPaths, version: str) -> None:
    version_tuple(version)
    paths.settings.mkdir(parents=True, exist_ok=True)
    marker = paths.settings / STATE_FILE
    temporary = marker.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({"product": PRODUCT, "version": version}, indent=2), encoding="utf-8")
    temporary.replace(marker)
