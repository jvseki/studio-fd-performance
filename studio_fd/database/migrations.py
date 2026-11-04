"""Aplica apenas migrações conhecidas; nunca recria tabelas existentes."""

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from studio_fd.utils.paths import resource_root


def migrate_database(engine: Engine) -> None:
    config = Config()
    # ConfigParser exige escape de % em caminhos de arquivos.
    location = str(resource_root() / "migrations").replace("%", "%%")
    config.set_main_option("script_location", location)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
