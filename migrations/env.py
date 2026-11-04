"""O aplicativo fornece a conexão: não há URL de banco fixa no código."""

from alembic import context

from studio_fd.database.base import Base
import studio_fd.models  # noqa: F401 — registra modelos para comparação de schema


connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Execute as migrações pelo aplicativo ou pelo serviço de banco.")

context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
