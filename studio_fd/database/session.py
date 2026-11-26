from pathlib import Path

from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from studio_fd.utils.formatting import search_key


def create_database_engine(path: Path) -> Engine:
    engine = create_engine(URL.create("sqlite", database=str(path)), connect_args={"timeout": 15})

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _record):
        connection.create_function("search_key", 1, search_key, deterministic=True)
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()

    return engine


def create_engine_from_url(url: str) -> Engine:
    """PostgreSQL da versão web (Supabase). O desktop continua em SQLite.

    A pesquisa sem acentos (search_key) é criada como função SQL na migração 0001.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    # Conexão sempre criptografada (o Supabase aceita; sem isso o driver poderia aceitar sem TLS).
    extra = {} if "sslmode=" in url else {"sslmode": "require"}
    return create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2, pool_recycle=300, connect_args=extra)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
