from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from studio_fd.database.base import Base


class Trainer(Base):
    """Personal do Studio. Cada personal ativo é uma coluna da agenda.

    A capacidade de um horário é o número de personais ativos: com dois
    personais, no máximo dois alunos por horário.
    """

    __tablename__ = "trainers"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        CheckConstraint("active IN (0, 1)", name="active_boolean"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
