r"""Gera o script SQL das tabelas para o Supabase (PostgreSQL), a partir das migrações.
Não conecta em banco nenhum. Uso: ..\..\.venv\Scripts\python.exe gerar_sql.py
"""

import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.schema import CreateTable  # noqa: E402

from acesso import usuarios  # noqa: E402

saida = io.StringIO()
config = Config(output_buffer=saida)
config.set_main_option("script_location", str(ROOT / "migrations"))
config.attributes["dialect"] = "postgresql"
command.upgrade(config, "head", sql=True)
usuarios_sql = str(CreateTable(usuarios, if_not_exists=True).compile(dialect=postgresql.dialect())).strip()
tabelas = ["alembic_version", "plans", "students", "trainers", "settings", "appointments", "payments",
           "cash_entries", "contracts", "anamneses", "web_usuarios"]
rls = "\n".join(f'ALTER TABLE public."{t}" ENABLE ROW LEVEL SECURITY;' for t in tabelas)
destino = Path(__file__).resolve().parents[1] / "supabase" / "criar_tabelas.sql"
destino.parent.mkdir(exist_ok=True)
destino.write_text(f"""-- Studio FD Performance — tabelas do banco (PostgreSQL / Supabase)
-- Gerado por versão-web/backend/gerar_sql.py a partir das migrações. Não edite à mão.
-- Uso opcional: o sistema cria tudo sozinho na primeira vez que conecta.
-- Rode UMA vez, num projeto vazio: Supabase > SQL Editor > New query > colar > Run.

{saida.getvalue().strip()}

-- Usuários da versão web (login)
{usuarios_sql};

-- Proteção: bloqueia a API automática do Supabase (o sistema acessa como dono das tabelas)
{rls}
""", encoding="utf-8", newline="\n")
print("gerado:", destino)
