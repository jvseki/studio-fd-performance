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


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
