from sqlalchemy import Boolean, CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from studio_fd.database.base import Base


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        CheckConstraint("workouts_per_week BETWEEN 1 AND 7", name="workouts_range"),
        CheckConstraint("price_cents >= 0", name="price_nonnegative"),
        CheckConstraint("duration_months > 0", name="duration_positive"),
        CheckConstraint("active IN (0, 1)", name="active_boolean"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    workouts_per_week: Mapped[int] = mapped_column(Integer)
    # Dinheiro em centavos inteiros evita arredondamentos de ponto flutuante.
    price_cents: Mapped[int] = mapped_column(Integer)
    duration_months: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
