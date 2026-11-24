"""Backup da versão web (PostgreSQL): um .zip com todos os dados em JSON e os PDFs.

O banco do Supabase grátis não tem backup restaurável garantido, então este
arquivo deve ser baixado e guardado fora com frequência (ex.: toda semana).
Senhas não entram no arquivo (nem os hashes).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.engine import Engine

from studio_fd import __version__
from studio_fd.database.base import Base
import studio_fd.models  # noqa: F401 (registra as tabelas)

from armazenamento import Armazenamento


def _valor(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    return v


def exportar(engine: Engine, pastas_locais: dict[str, Path], armazenamento: Armazenamento) -> tuple[str, bytes]:
    tabelas: dict[str, list[dict]] = {}
    with engine.connect() as conexao:
        for tabela in Base.metadata.sorted_tables:
            tabelas[tabela.name] = [{k: _valor(v) for k, v in linha._mapping.items()} for linha in conexao.execute(select(tabela))]
        revisao = conexao.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
    buffer = io.BytesIO()
    manifesto = {"product": "studio-fd-performance", "format": "web-json-1", "app_version": __version__, "schema_revision": revisao,
                 "created_at": datetime.now(timezone.utc).isoformat(), "counts": {k: len(v) for k, v in tabelas.items()}, "files": {}}
    with ZipFile(buffer, "w", ZIP_DEFLATED) as arquivo:
        dados = json.dumps(tabelas, ensure_ascii=False, indent=1).encode("utf-8")
        arquivo.writestr("dados.json", dados)
        manifesto["files"]["dados.json"] = hashlib.sha256(dados).hexdigest()
        for pasta, local in pastas_locais.items():
            nomes = {p.relative_to(local).as_posix() for p in local.rglob("*.pdf")} if local.exists() else set()
            for registro in tabelas.get("contracts" if pasta == "contratos" else "anamneses", []):
                if registro.get("file_path"):
                    nomes.add(registro["file_path"])
            for nome in sorted(nomes):
                conteudo = (local / nome).read_bytes() if (local / nome).exists() else armazenamento.baixar(f"{pasta}/{nome}")
                if conteudo:
                    arquivo.writestr(f"{pasta}/{nome}", conteudo)
                    manifesto["files"][f"{pasta}/{nome}"] = hashlib.sha256(conteudo).hexdigest()
        arquivo.writestr("manifest.json", json.dumps(manifesto, ensure_ascii=False, indent=2))
    return f"StudioFD_Web_{date.today():%Y-%m-%d}.zip", buffer.getvalue()
