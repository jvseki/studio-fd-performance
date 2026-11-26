"""Backup da versão web (PostgreSQL) no MESMO formato do programa do computador (.fdbkp).

Assim, o arquivo baixado na web pode ser restaurado no Studio FD do computador
(Backup → Restaurar), servindo de cópia de segurança fora da nuvem.

Como é feito: cria um banco SQLite temporário com a mesma estrutura (migrações),
copia todas as tabelas do Supabase para ele, junta os PDFs e usa o próprio
BackupService do desktop para empacotar e conferir (SHA-256 e integridade).
Senhas e logins da web (tabela web_usuarios) NÃO entram no arquivo.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from sqlalchemy import insert, select
from sqlalchemy.engine import Engine

from studio_fd import __version__
from studio_fd.database.base import Base
from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine
from studio_fd.services.backup_service import BackupService
from studio_fd.utils.paths import AppPaths
import studio_fd.models  # noqa: F401 (registra as tabelas)

from armazenamento import Armazenamento


def _nome_seguro(nome: str) -> bool:
    partes = PurePosixPath(nome).parts
    return bool(partes) and not nome.startswith("/") and "\\" not in nome and ".." not in partes and ":" not in nome


def _copiar_tabelas(origem: Engine, destino: Engine) -> dict[str, list[str]]:
    """Copia tudo e devolve os nomes dos PDFs citados em contratos e anamneses."""
    tabelas = Base.metadata.sorted_tables
    pdfs: dict[str, list[str]] = {"contratos": [], "anamneses": []}
    with origem.connect() as leitura, destino.begin() as escrita:
        for tabela in reversed(tabelas):  # as migrações já trazem personais/configurações padrão
            escrita.execute(tabela.delete())
        for tabela in tabelas:
            linhas = [dict(linha._mapping) for linha in leitura.execute(select(tabela))]
            if linhas:
                escrita.execute(insert(tabela), linhas)
            pasta = {"contracts": "contratos", "anamneses": "anamneses"}.get(tabela.name)
            if pasta:
                pdfs[pasta] = [linha["file_path"] for linha in linhas if linha.get("file_path")]
    return pdfs


def exportar(engine: Engine, pastas_locais: dict[str, Path], armazenamento: Armazenamento) -> tuple[str, bytes]:
    with TemporaryDirectory(prefix="backup-web-") as temporaria:
        paths = AppPaths(Path(temporaria) / "dados")
        paths.ensure_directories()
        banco = create_database_engine(paths.database)
        try:
            migrate_database(banco)
            pdfs = _copiar_tabelas(engine, banco)
        finally:
            banco.dispose()
        destinos = {"contratos": paths.contracts, "anamneses": paths.anamneses}
        for pasta, nomes in pdfs.items():
            local = pastas_locais.get(pasta)
            for nome in nomes:
                if not _nome_seguro(nome):
                    continue
                conteudo = (local / nome).read_bytes() if local and (local / nome).is_file() else armazenamento.baixar(f"{pasta}/{nome}")
                if conteudo:
                    alvo = destinos[pasta] / nome
                    alvo.parent.mkdir(parents=True, exist_ok=True)
                    alvo.write_bytes(conteudo)
        servico = BackupService(paths, __version__)
        arquivo = servico.export(Path(temporaria) / "saida" / servico.default_name(), reason="web")
        return arquivo.name, arquivo.read_bytes()
