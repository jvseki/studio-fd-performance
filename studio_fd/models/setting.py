from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from studio_fd.database.base import Base


class Setting(Base):
    """Preferências do Studio em pares chave/valor. Ficam no banco para
    viajarem junto com o backup."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
