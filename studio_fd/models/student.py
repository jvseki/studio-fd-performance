from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studio_fd.database.base import Base
from studio_fd.models.plan import Plan


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("length(trim(full_name)) > 0", name="name_not_empty"),
        CheckConstraint("monthly_fee_cents IS NULL OR monthly_fee_cents >= 0", name="fee_nonnegative"),
        CheckConstraint("due_day IS NULL OR due_day BETWEEN 1 AND 31", name="due_day_range"),
        CheckConstraint("active IN (0, 1)", name="active_boolean"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    phone: Mapped[str] = mapped_column(String(30))
    birth_date: Mapped[date | None] = mapped_column(Date)
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True)
    address: Mapped[str | None] = mapped_column(String(255))
    registered_on: Mapped[date] = mapped_column(Date, default=date.today)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    notes: Mapped[str | None] = mapped_column(Text)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    monthly_fee_cents: Mapped[int | None] = mapped_column(Integer)
    starts_on: Mapped[date | None] = mapped_column(Date)
    due_day: Mapped[int | None] = mapped_column(Integer)
    plan: Mapped[Plan | None] = relationship()
